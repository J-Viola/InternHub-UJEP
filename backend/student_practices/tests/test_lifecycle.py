import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from docx import Document
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class StudentPracticeLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Setup Environment
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)

        # 2. Setup Users
        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )
        self.other_student = StudentUser.objects.create(email="other@test.com", first_name="Petr", last_name="Cizi", is_active=True)

        self.org_user = OrganizationUser.objects.create(
            email="org@test.com",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer_profile
        self.org_user.save()

        # 3. Setup Professor — garant praxe katedry IT (role pro state machine přechody)
        self.professor = ProfessorUser.objects.create_user(
            email="prof@test.com",
            password="password123",
            first_name="Alice",
            last_name="Prof",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )

        # 4. Setup Practice
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

    def _apply(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post("/api/practices/student/apply/", {"practice": self.practice.practice_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sp = StudentPractice.objects.get(user=self.student, practice=self.practice)
        if not sp.contract_document:
            DocumentHelper.assign_default_documents(sp)
            sp.refresh_from_db()
        return sp

    def _transition(self, user, sp, target_state):
        self.client.force_authenticate(user=user)
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": target_state.value},
            format="json",
        )

    def test_full_lifecycle_state_machine(self):
        # 1. Student Applies -> APPLIED
        student_practice = self._apply()
        self.assertEqual(student_practice.workflow_state, StudentPracticeWorkflowState.APPLIED)

        # 2. Professor (garant) approves -> PRELIMINARY_APPROVED (school approval)
        response = self._transition(self.professor, student_practice, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_practice.refresh_from_db()
        self.assertEqual(student_practice.workflow_state, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        self.assertTrue(student_practice.school_approved)

        # 3. Organization approves -> AWAITING_CONTRACT (contract preparation)
        response = self._transition(self.org_user, student_practice, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_practice.refresh_from_db()
        self.assertEqual(student_practice.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)

        # 4. Student uploads contract document -> auto AWAITING_DOCUMENTS
        self.client.force_authenticate(user=self.student)
        contract_doc = student_practice.contract_document
        upload_url = f"/api/student-practices/upload-document/{contract_doc.document_id}"
        buf = io.BytesIO()
        Document().save(buf)
        buf.seek(0)
        file = SimpleUploadedFile(
            "contract.docx",
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(upload_url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        student_practice.refresh_from_db()
        self.assertEqual(student_practice.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)

        # 5. Organizace potvrdí převzetí smlouvy (employer_approved)
        self.client.force_authenticate(user=self.org_user)
        response = self.client.post(
            f"/api/student-practices/{student_practice.student_practice_id}/confirm-contract/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_practice.refresh_from_db()
        self.assertTrue(student_practice.employer_approved)
        self.assertNotEqual(student_practice.workflow_state, StudentPracticeWorkflowState.CONTRACTED)

        # 6. Garant schválí dokument smlouvy -> CONTRACTED
        review_url = f"/api/student-practices/review-document/{contract_doc.document_id}"
        self.client.force_authenticate(user=self.professor)
        response = self.client.patch(review_url, {"status": 1})  # DocumentStatus.APPROVED
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_practice.refresh_from_db()
        self.assertEqual(student_practice.workflow_state, StudentPracticeWorkflowState.CONTRACTED)

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
        transition_url = f"/api/student-practices/{student_practice.student_practice_id}/transition/"

        # Other student tries to approve -> 400 (role check)
        self.client.force_authenticate(user=self.other_student)
        response = self.client.post(
            transition_url,
            {"target_state": StudentPracticeWorkflowState.PRELIMINARY_APPROVED.value},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_workflow_status_label_unknown(self):
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
        url = f"/api/student-practices/{student_practice.student_practice_id}"

        self.client.force_authenticate(user=self.student)

        # Test with Czech header (should return "Neznámý" since workflow_state is None)
        response_cs = self.client.get(url, HTTP_ACCEPT_LANGUAGE="cs")
        self.assertEqual(response_cs.status_code, status.HTTP_200_OK)
        self.assertEqual(response_cs.data["workflow_status_label"], "Neznámý")
