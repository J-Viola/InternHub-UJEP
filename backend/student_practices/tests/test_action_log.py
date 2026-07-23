"""
Tests for UC-03 — ActionLog / Timeline entries.

Covers:
- ActionLog creation on state transitions
- ActionLog creation on rejection
- ActionLog creation on withdraw
- ActionLog creation on document upload
- ActionLog creation on document review
- GET history endpoint returns proper format
- GET history endpoint — access only for participants
- ActionLogSerializer field format
"""

import io
import zipfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.serializers import ActionLogSerializer
from student_practices.services import StudentPracticeService
from subject.models import Subject
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
    StudentUser,
    UserSubject,
    UserSubjectType,
)


class StudentPracticeActionLogTests(TestCase):
    """UC-03: Akční log / Timeline — tvorba záznamů a history endpoint."""

    def setUp(self):
        self.client = APIClient()

        # -- Users --
        self.student = StudentUser.objects.create(
            email="student@actionlog.test",
            first_name="Jan",
            last_name="Novák",
            is_active=True,
        )
        self.other_student = StudentUser.objects.create(
            email="other@actionlog.test",
            first_name="Petr",
            last_name="Svoboda",
            is_active=True,
        )
        self.org_user = OrganizationUser.objects.create(
            email="org@actionlog.test",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="ActionLog Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # -- Department & Subject --
        self.department = Department.objects.create(
            department_name="Informatika",
            department_code="KI",
        )
        self.subject = Subject.objects.create(
            subject_name="Odborná praxe",
            subject_code="KI/BOP",
            department=self.department,
            min_hours=480,
        )

        # -- Professor --
        self.stag_role = StagRole.objects.create(
            role=StagRoleEnum.VY,
            role_name="Vyučující",
        )
        self.professor = ProfessorUser.objects.create(
            email="prof@actionlog.test",
            first_name="Prof",
            last_name="Test",
            is_active=True,
            department=self.department,
            stag_role=self.stag_role,
            department_role=DepartmentRole.TEACHER,
        )
        # Link professor to subject for document review permission
        UserSubject.objects.create(
            user=self.professor,
            subject=self.subject,
            role=UserSubjectType.Professor,
        )

        # -- Practice --
        self.practice = Practice.objects.create(
            title="ActionLog Test Practice",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=65),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            is_active=True,
        )

        # -- StudentPractice in APPLIED state --
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
        )

        # Assign default documents
        DocumentHelper.assign_default_documents(self.sp)
        self.sp.refresh_from_db()
        self.contract_doc = self.sp.contract_document

        # URLs
        self.history_url = f"/api/student-practices/{self.sp.student_practice_id}/history/"
        self.upload_url = f"/api/student-practices/upload-document/{self.contract_doc.document_id}"

    # ------------------------------------------------------------------
    # Helper: create a minimal valid .docx
    # ------------------------------------------------------------------

    def _make_docx(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
        buf.seek(0)
        return buf

    # ------------------------------------------------------------------
    # 1) State transition → ActionLog
    # ------------------------------------------------------------------

    def test_action_log_on_state_transition(self):
        """State transition (APPLIED → PRELIMINARY_APPROVED) creates STATE_TRANSITION ActionLog."""
        StudentPracticeService.transition_student_practice_state(
            sp=self.sp,
            target_state=StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            actor=self.professor,
        )
        self.sp.refresh_from_db()
        self.assertEqual(
            self.sp.workflow_state,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
        )

        logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            action_type=ActionLogType.STATE_TRANSITION,
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn(
            "PRELIMINARY_APPROVED",
            logs[0].action_description,
        )

    # ------------------------------------------------------------------
    # 2) Rejection → ActionLog
    # ------------------------------------------------------------------

    def test_action_log_on_rejection(self):
        """Rejection (APPLIED → REJECTED) creates REJECT ActionLog."""
        StudentPracticeService.transition_student_practice_state(
            sp=self.sp,
            target_state=StudentPracticeWorkflowState.REJECTED,
            actor=self.professor,
            reason="Nesplňuje požadavky.",
        )
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.REJECTED)

        logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            action_type=ActionLogType.REJECT,
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn("REJECTED", logs[0].action_description)

    # ------------------------------------------------------------------
    # 3) Withdraw → ActionLog
    # ------------------------------------------------------------------

    def test_action_log_on_withdraw(self):
        """Withdraw creates STORNO ActionLog."""
        from student_practices.services import withdraw_student_practice

        withdraw_student_practice(sp=self.sp, actor=self.student)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.REJECTED)

        logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            action_type=ActionLogType.STORNO,
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn("stahl", logs[0].action_description.lower())

    # ------------------------------------------------------------------
    # 4) Document upload → ActionLog
    # ------------------------------------------------------------------

    def test_action_log_on_document_upload(self):
        """Document upload creates DOCUMENT_UPLOAD ActionLog."""
        self.client.force_authenticate(user=self.student)
        docx_buf = self._make_docx()
        file = SimpleUploadedFile(
            "contract.docx",
            docx_buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(self.upload_url, {"document": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        logs = ActionLog.objects.filter(
            object_type="UploadedDocument",
            object_id=self.contract_doc.document_id,
            action_type=ActionLogType.DOCUMENT_UPLOAD,
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn(self.student.email, logs[0].action_description)

    # ------------------------------------------------------------------
    # 5) Document review (approve) → ActionLog
    # ------------------------------------------------------------------

    def test_action_log_on_document_review(self):
        """Document review (approve) creates DOCUMENT_REVIEW ActionLog."""
        StudentPracticeService.process_document_review(
            user=self.professor,
            document_id=self.contract_doc.document_id,
            status_val=DocumentStatus.APPROVED.value,
            review_note="Schváleno.",
        )

        logs = ActionLog.objects.filter(
            object_type="UploadedDocument",
            object_id=self.contract_doc.document_id,
            action_type=ActionLogType.DOCUMENT_REVIEW,
        )
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn("schválen", logs[0].action_description.lower())

    # ------------------------------------------------------------------
    # 6) GET history endpoint → proper format
    # ------------------------------------------------------------------

    def test_action_log_history_endpoint(self):
        """GET history endpoint returns proper format (list with expected fields)."""
        # Create a few ActionLog entries first
        ActionLogService.log(
            user=self.student,
            action_type=ActionLogType.CREATE,
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            description="Přihláška vytvořena",
        )
        ActionLogService.log(
            user=self.student,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            description="Přihláška zobrazena",
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)

        entry = response.data[0]
        self.assertIn("action_id", entry)
        self.assertIn("user_name", entry)
        self.assertIn("action_type", entry)
        self.assertIn("action_description", entry)
        self.assertIn("action_date", entry)

    # ------------------------------------------------------------------
    # 7) GET history endpoint → access denied for non-participant
    # ------------------------------------------------------------------

    def test_action_log_history_access_denied(self):
        """Non-participant student gets 403 on history endpoint."""
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # 8) ActionLogSerializer → expected fields
    # ------------------------------------------------------------------

    def test_action_log_serializer_format(self):
        """ActionLogSerializer returns expected fields."""
        log_entry = ActionLog.objects.create(
            user=self.student,
            action_type=ActionLogType.CREATE,
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            action_description="Test description",
            action_date=timezone.now(),
        )
        serializer = ActionLogSerializer(log_entry)
        data = serializer.data

        self.assertIn("action_id", data)
        self.assertIn("user_name", data)
        self.assertIn("action_type", data)
        self.assertIn("action_description", data)
        self.assertIn("action_date", data)
        self.assertEqual(data["action_type"], ActionLogType.CREATE)
        self.assertEqual(data["action_description"], "Test description")
        self.assertEqual(data["user_name"], self.student.full_name)
