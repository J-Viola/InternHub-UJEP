from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
)
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class StudentPracticeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.student = StudentUser.objects.create(email="student@test.com", first_name="S", last_name="U", is_active=True)
        self.other_student = StudentUser.objects.create(email="other@test.com", first_name="O", last_name="S", is_active=True)
        self.employer_user = OrganizationUser.objects.create(email="emp@test.com", first_name="E", last_name="O", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.employer_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.employer_user.employer_profile = self.employer_profile
        self.employer_user.save()

        # Practice
        self.practice = Practice.objects.create(
            title="Test Practice",
            coefficient=1.0,
            employer=self.employer_profile,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            is_active=True,
        )

        # Invitation
        self.invitation = EmployerInvitation.objects.create(
            user=self.student,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            employer=self.employer_profile,
        )

    def test_employer_invitation_approval_success(self):
        self.client.force_authenticate(user=self.student)
        url = "/api/student-practices/employer-invitation/approve/"

        data = {"invitation_id": self.invitation.invitation_id, "action": "accept"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, EmployerInvitationStatus.ACCEPTED)

    def test_upload_document_permission_denied_for_other_student(self):
        # Create StudentPractice for this test case
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        self.client.force_authenticate(user=self.other_student)
        url = f"/api/student-practices/upload-document/{contract_doc.document_id}"

        file = SimpleUploadedFile(
            "contract.docx",
            b"content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        data = {"document": file}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_document_success_for_owner(self):
        import io
        import zipfile

        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{contract_doc.document_id}"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
        buf.seek(0)

        file = SimpleUploadedFile(
            "contract.docx",
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        data = {"document": file}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_document_permission_denied(self):
        # Create StudentPractice for this test case
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        self.client.force_authenticate(user=self.other_student)
        url = f"/api/student-practices/download-document/{contract_doc.document_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_document_success(self):
        # Create StudentPractice for this test case
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/download-document/{contract_doc.document_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_review_student_cannot_approve_own_document(self):
        """
        C-M4-C1: A student must not be able to approve/review a document
        via the review endpoint — should return 403, not 500.
        """
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/review-document/{contract_doc.document_id}"
        response = self.client.patch(url, {"status": DocumentStatus.APPROVED.value}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_document_review_permission_denied_returns_403_not_500(self):
        """
        C-M4-C1: An unauthorized professor (not subject teacher, not head)
        must receive 403, not 500, when calling the document review endpoint.
        """
        dept = Department.objects.create(department_name="Fyzika", department_code="FYZ")
        subj = Subject.objects.create(subject_name="Fyzika Praxe", subject_code="FYZP", department=dept)
        practice_with_subj = Practice.objects.create(
            title="Physics Practice",
            coefficient=1.0,
            employer=self.employer_profile,
            subject=subj,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

        sp = StudentPractice.objects.create(
            user=self.student,
            practice=practice_with_subj,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        DocumentHelper.assign_default_documents(sp)
        sp.refresh_from_db()
        contract_doc = sp.contract_document

        # Create a professor NOT associated with the subject/department
        other_dept = Department.objects.create(department_name="Chemie", department_code="CHE")
        unauthorized_prof = ProfessorUser.objects.create_user(
            email="unauth_prof@test.com",
            password="password123",
            first_name="Un",
            last_name="Auth",
            is_active=True,
            department=other_dept,
            department_role=DepartmentRole.TEACHER,
        )

        self.client.force_authenticate(user=unauthorized_prof)
        url = f"/api/student-practices/review-document/{contract_doc.document_id}"
        response = self.client.patch(url, {"status": DocumentStatus.APPROVED.value}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
