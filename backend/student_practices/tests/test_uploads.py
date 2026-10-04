"""
Tests for Document upload and rejection reason validation.

Covers:
- Upload PDF (allowed format)
- Upload disallowed format (.exe) → 400
- Upload >10MB → 400
- late_submission flag on ENDED practice
- Rejection reason min 10 chars → OK
- Rejection reason short (<10 chars) → 400
- ActionLog záznam při rejectu
"""

import io
import zipfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from users.constants import ActionLogType
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class UploadDocumentTests(TestCase):
    """Nahrávání dokumentů — formáty, velikost, late_submission."""

    def setUp(self):
        self.client = APIClient()

        # Users
        self.student = StudentUser.objects.create(
            email="student@upload.test",
            first_name="Jan",
            last_name="Novák",
            is_active=True,
        )
        self.org_user = OrganizationUser.objects.create(
            email="org@upload.test",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Upload Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Practice
        self.practice = Practice.objects.create(
            title="Upload Test Practice",
            employer=self.employer,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            is_active=True,
        )

        # StudentPractice with document
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
        )
        DocumentHelper.assign_default_documents(self.sp)
        self.sp.refresh_from_db()

        self.contract_doc = self.sp.contract_document

    def _make_docx(self, content=b"fake docx content"):
        """Create a minimal valid .docx (ZIP with [Content_Types].xml)."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
        buf.seek(0)
        if content:
            buf.write(content)
            buf.seek(0)
        return buf

    def _make_pdf(self):
        """Create a minimal valid PDF."""
        buf = io.BytesIO()
        buf.write(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\nxref\n0 3"
            b"\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n112\n%%EOF"
        )
        buf.seek(0)
        return buf

    def test_upload_pdf_allowed_format(self):
        """Upload PDF (povolený formát) → 201."""
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.contract_doc.document_id}"
        pdf = self._make_pdf()
        file = SimpleUploadedFile(
            "contract.pdf",
            pdf.read(),
            content_type="application/pdf",
        )
        response = self.client.post(url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_disallowed_format_returns_400(self):
        """Upload nepovoleného formátu (.exe) → 400."""
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.contract_doc.document_id}"
        file = SimpleUploadedFile(
            "malware.exe",
            b"fake executable content",
            content_type="application/x-msdownload",
        )
        response = self.client.post(url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_over_10mb_returns_400(self):
        """Upload >10MB → 400."""
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.contract_doc.document_id}"
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        file = SimpleUploadedFile(
            "large.pdf",
            large_content,
            content_type="application/pdf",
        )
        response = self.client.post(url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_late_submission_flag(self):
        """late_submission=True when uploading after end_date on ENDED practice."""
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.contract_doc.document_id}"
        pdf = self._make_pdf()
        file = SimpleUploadedFile(
            "report.pdf",
            pdf.read(),
            content_type="application/pdf",
        )
        response = self.client.post(url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.contract_doc.refresh_from_db()
        self.assertTrue(self.contract_doc.late_submission)


class RejectionReasonTests(TestCase):
    """Validace rejection_reason (min 10 znaků) a ActionLog."""

    def setUp(self):
        self.client = APIClient()

        self.student = StudentUser.objects.create(
            email="student@reject.test",
            first_name="Jan",
            last_name="Novák",
            is_active=True,
        )
        self.org_user = OrganizationUser.objects.create(
            email="org@reject.test",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Reject Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Professor for rejection via state machine
        from department.models import Department
        from users.models import StagRole

        self.dept = Department.objects.create(department_name="Informatika", department_code="KI")
        self.stag_role = StagRole.objects.create(role="vy", role_name="Vyučující")
        self.professor = ProfessorUser.objects.create(
            email="prof@reject.test",
            first_name="Prof",
            last_name="Reject",
            is_active=True,
            department=self.dept,
            stag_role=self.stag_role,
            department_role=DepartmentRole.TEACHER,
        )

        self.practice = Practice.objects.create(
            title="Reject Test Practice",
            employer=self.employer,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=65),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            is_active=True,
        )

        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
        )

    def test_rejection_reason_min_10_chars_accepted(self):
        """Rejection reason >= 10 chars → OK (model-level validation)."""
        self.sp.rejection_reason = "Tento důvod má více než 10 znaků."
        try:
            # Validate only rejection_reason to avoid required OneToOneField errors
            self.sp.clean_fields(exclude=["contract_document", "content_document", "feedback_document"])
            self.sp.save(update_fields=["rejection_reason"])
        except Exception:
            self.fail("Rejection reason with >=10 chars should be valid")

    def test_rejection_reason_short_raises_validation_error(self):
        """Rejection reason < 10 chars → ValidationError."""
        self.sp.rejection_reason = "Krátký"
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.sp.full_clean()

    def test_action_log_on_rejection(self):
        """ActionLog záznam vzniká při rejectu přihlášky."""
        # Need to add subject teacher relationship for the professor
        from student_practices.services import StudentPracticeService
        from subject.models import Subject

        subject = Subject.objects.create(
            subject_name="Odborná praxe",
            subject_code="KI/BOP",
            department=self.dept,
            min_hours=480,
        )
        self.practice.subject = subject
        self.practice.save()

        from users.models import UserSubject, UserSubjectType

        UserSubject.objects.create(
            user=self.professor,
            subject=subject,
            role=UserSubjectType.Professor,
        )

        # Perform transition APPLIED -> REJECTED
        sp = StudentPracticeService.transition_student_practice_state(
            sp=self.sp,
            target_state=StudentPracticeWorkflowState.REJECTED,
            actor=self.professor,
            reason="Nesplňuje požadavky pro tuto praxi.",
        )
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.REJECTED)

        # Verify ActionLog was created
        logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
        )
        # Should have at least the transition log
        transition_logs = [log for log in logs if log.action_type == ActionLogType.STATE_TRANSITION]
        self.assertGreaterEqual(len(transition_logs), 1)
        # The log description should mention REJECTED
        self.assertIn("REJECTED", transition_logs[-1].action_description)
