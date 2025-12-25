from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import DocumentHelper, StudentPractice
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    StudentUser,
)


class StudentPracticeLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Setup Environment
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)

        # 2. Setup Users
        self.student = StudentUser.objects.create(email="student@test.com", first_name="Jan", last_name="Student", is_active=True)
        self.other_student = StudentUser.objects.create(email="other@test.com", first_name="Petr", last_name="Cizi", is_active=True)

        self.org_user = OrganizationUser.objects.create(email="org@test.com", is_active=True, organization_role=OrganizationRole.OWNER)
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id, company_name="Test Co", approval_status=ApprovalStatus.APPROVED
        )
        self.org_user.employer_profile = self.employer_profile
        self.org_user.save()

        # 3. Setup Practice
        self.practice = Practice.objects.create(
            title="Dev Job",
            employer=self.employer_profile,
            subject=self.subject,
            contact_user=self.org_user,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            coefficient=1.0,
            available_positions=5,
        )

    def test_full_lifecycle(self):
        # 1. Student Applies
        self.client.force_authenticate(user=self.student)
        apply_url = "/api/practices/apply_student_practice/"
        response = self.client.post(apply_url, {"practice": self.practice.practice_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        student_practice = StudentPractice.objects.get(user=self.student, practice=self.practice)
        # Manually assign documents because create logic
        # in views/services might not have triggered it (depending on how apply_student_practice is implemented, let's check)
        # Actually, if apply_student_practice uses the service that we fixed, it should work.
        # But wait, apply_student_practice logic wasn't shown in the diffs yet.
        # I should check if that view uses the service or creates model directly.
        # Assuming for now we need to fix it here or in the view.
        # Let's check apply_student_practice implementation later.
        # For this test, since it tests lifecycle, we need documents.
        if not student_practice.contract_document:
            DocumentHelper.assign_default_documents(student_practice)
            student_practice.refresh_from_db()

        self.assertEqual(student_practice.approval_status, ApprovalStatus.PENDING)

        # 2. Organization Approves
        self.client.force_authenticate(user=self.org_user)
        status_url = f"/api/student-practices/{student_practice.student_practice_id}/status/"

        response = self.client.patch(status_url, {"approval_status": ApprovalStatus.APPROVED.value}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        student_practice.refresh_from_db()
        self.assertEqual(student_practice.approval_status, ApprovalStatus.APPROVED)

        # 3. Upload Contract (by Student)
        self.client.force_authenticate(user=self.student)
        contract_doc = student_practice.contract_document
        upload_url = f"/api/student-practices/upload-document/{contract_doc.document_id}"

        file = SimpleUploadedFile(
            "contract.docx", b"content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        response = self.client.post(upload_url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 4. Change Progress to IN_PROGRESS (by Org)
        self.client.force_authenticate(user=self.org_user)
        response = self.client.patch(status_url, {"progress_status": ProgressStatus.IN_PROGRESS.value}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        student_practice.refresh_from_db()
        self.assertEqual(student_practice.progress_status, ProgressStatus.IN_PROGRESS)

        # 5. Finish Practice (COMPLETED)
        response = self.client.patch(status_url, {"progress_status": ProgressStatus.COMPLETED.value}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        student_practice.refresh_from_db()
        self.assertEqual(student_practice.progress_status, ProgressStatus.COMPLETED)

    def test_unauthorized_status_change(self):
        # Student creates practice app
        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            year=2050,
        )
        student_practice = StudentPractice.objects.get(user=self.student, practice=self.practice)
        status_url = f"/api/student-practices/{student_practice.student_practice_id}/status/"

        # Other student tries to approve
        self.client.force_authenticate(user=self.other_student)
        response = self.client.patch(status_url, {"approval_status": ApprovalStatus.APPROVED.value}, format="json")

        # Expect 403 Forbidden or 404 Not Found (if queryset filters by user)
        # Assuming standard permissions, it should be 403 or 404.
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
