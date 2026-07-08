from datetime import date

from django.core import mail
from django.test import TestCase, override_settings

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.messages import StudentPracticeMessages
from student_practices.models import (
    DocumentHelper,
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.services import StudentPracticeService
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


class StudentPracticeServiceTests(TestCase):
    def setUp(self):
        self.user = StudentUser.objects.create(email="student@test.com", first_name="S", last_name="U")
        self.other_user = StudentUser.objects.create(email="thief@test.com", first_name="T", last_name="H")
        self.employer_user = OrganizationUser.objects.create(email="emp@test.com", first_name="E", last_name="O")
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.employer_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )

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
        self.invitation = EmployerInvitation.objects.create(
            user=self.user,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            employer=self.employer_profile,
        )

    def test_process_invitation_approval_accept(self):
        # Ensure StudentPractice does not exist initially for this specific test
        StudentPractice.objects.filter(user=self.user, practice=self.practice).delete()

        result = StudentPracticeService.process_invitation_approval(self.user, self.invitation.invitation_id, "accept")

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, EmployerInvitationStatus.ACCEPTED)

        sp = StudentPractice.objects.get(user=self.user, practice=self.practice)
        # Now it's PENDING until school approves
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(sp.progress_status, ProgressStatus.NOT_STARTED)
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)
        self.assertIn("student_practice_id", result)

    def test_process_invitation_approval_reject(self):
        StudentPracticeService.process_invitation_approval(self.user, self.invitation.invitation_id, "reject")

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, EmployerInvitationStatus.REJECTED)
        self.assertFalse(StudentPractice.objects.filter(user=self.user, practice=self.practice).exists())

    def test_process_invitation_approval_invalid_action(self):
        with self.assertRaises(ValueError):
            StudentPracticeService.process_invitation_approval(self.user, self.invitation.invitation_id, "invalid")

    def test_process_invitation_not_found(self):
        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(self.user, 999, "accept")
        self.assertIn("INVITATION_NOT_FOUND", str(cm.exception))

    def test_process_invitation_already_processed(self):
        self.invitation.status = EmployerInvitationStatus.ACCEPTED
        self.invitation.save()

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(self.user, self.invitation.invitation_id, "accept")
        self.assertIn("INVITATION_PROCESSED", str(cm.exception))

    def test_process_invitation_wrong_user(self):
        other_user = StudentUser.objects.create(email="other@student.cz", is_active=True)
        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(other_user, self.invitation.invitation_id, "accept")
        self.assertIn("INVITATION_NOT_FOUND", str(cm.exception))

    def test_update_student_practice_status_syncs_workflow_state(self):
        """
        C-M4-C2: Verify that update_student_practice_status correctly syncs
        workflow_state for all dual-approval transitions (PRELIMINARY_APPROVED,
        CONTRACTED, REJECTED), not just STARTED from evaluate_practice_readiness.
        """
        # Setup: department, subject, professor (head), org user
        dept = Department.objects.create(department_name="KIV", department_code="KIV")
        subj = Subject.objects.create(subject_name="SW Praxe", subject_code="SWP", department=dept)

        org_user = OrganizationUser.objects.create(
            email="org_test@test.com",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        org_profile = EmployerProfile.objects.create(
            employer_id=org_user.id,
            company_name="Test Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        org_user.employer_profile = org_profile
        org_user.save()

        prof = ProfessorUser.objects.create_user(
            email="prof_kiv@test.com",
            password="password123",
            first_name="Karel",
            last_name="Vyucujici",
            is_active=True,
            department=dept,
            department_role=DepartmentRole.HEAD,
        )

        practice = Practice.objects.create(
            title="KIV Praxe",
            coefficient=1.0,
            employer=org_profile,
            subject=subj,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

        sp = StudentPractice.objects.create(
            user=self.user,
            practice=practice,
            application_date=date.today(),
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        # --- 1. Employer approves → employer_approved=True, should be PRELIMINARY_APPROVED ---
        StudentPracticeService.update_student_practice_status(
            user=org_user,
            student_practice_id=sp.student_practice_id,
            data={"approval_status": ApprovalStatus.APPROVED.value},
        )
        sp.refresh_from_db()
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)
        self.assertEqual(
            sp.workflow_state, StudentPracticeWorkflowState.PRELIMINARY_APPROVED, "Employer-only approval should set PRELIMINARY_APPROVED"
        )

        # --- 2. Professor (head) approves → both flags, should be CONTRACTED ---
        StudentPracticeService.update_student_practice_status(
            user=prof,
            student_practice_id=sp.student_practice_id,
            data={"approval_status": ApprovalStatus.APPROVED.value},
        )
        sp.refresh_from_db()
        self.assertTrue(sp.school_approved)
        self.assertTrue(sp.employer_approved)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED, "Both approved should set CONTRACTED")

        # Cancel sp so we can create sp2 (unique constraint on active applications)
        sp.is_cancelled = True
        sp.save()

        # --- 3. Test REJECTED transition ---
        sp2 = StudentPractice.objects.create(
            user=self.user,
            practice=practice,
            application_date=date.today(),
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        StudentPracticeService.update_student_practice_status(
            user=prof,
            student_practice_id=sp2.student_practice_id,
            data={"approval_status": ApprovalStatus.REJECTED.value},
        )
        sp2.refresh_from_db()
        self.assertEqual(sp2.approval_status, ApprovalStatus.REJECTED)
        self.assertEqual(sp2.workflow_state, StudentPracticeWorkflowState.REJECTED, "Rejected should set REJECTED")

    # --- M-M4-1: Error messages use StudentPracticeMessages constants ---

    def test_cancelled_cannot_transition(self):
        """Transition on a cancelled SP raises using messages constant."""
        sp = self._create_student_practice()
        sp.is_cancelled = True
        sp.save()

        from student_practices.models import StudentPracticeWorkflowState

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.PRELIMINARY_APPROVED, self.user)
        self.assertIn(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY, str(cm.exception))

    def test_reapply_uses_constants(self):
        """Reapply validations use StudentPracticeMessages constants."""
        # Test: non-existent practice
        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.reapply_to_practice(self.user, 99999)
        self.assertIn(StudentPracticeMessages.PRACTICE_NOT_FOUND_OR_INACTIVE, str(cm.exception))

        # Test: capacity full
        from practices.models import PracticeWorkflowState

        self.practice.is_active = True
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.available_positions = 0
        self.practice.save()

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.reapply_to_practice(self.user, self.practice.practice_id)
        self.assertIn(StudentPracticeMessages.CAPACITY_FULL, str(cm.exception))

    def test_cancel_requires_reason_constant(self):
        """Cancel without reason uses message constant."""
        sp = self._create_student_practice()

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.cancel_student_practice(sp, self.user, "")
        self.assertIn(StudentPracticeMessages.CANCELLATION_REASON_REQUIRED, str(cm.exception))

    # --- M-M4-2: Cancel sends email notifications ---

    def _create_student_practice(self):
        """Helper to create a non-cancelled StudentPractice."""
        # Ensure practice has a contact_user for org notifications
        self.practice.contact_user = self.employer_user
        self.practice.save()

        sp = StudentPractice.objects.create(
            user=self.user,
            practice=self.practice,
            application_date=date.today(),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            hours_completed=0,
            year=date.today().year,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
        return sp

    def test_cancel_sends_emails(self):
        """Cancellation sends email notifications to student and org."""
        sp = self._create_student_practice()
        reason = "Duplicita prihlasky"

        StudentPracticeService.cancel_student_practice(sp, self.user, reason)

        self.assertEqual(len(mail.outbox), 2, f"Expected 2 emails, got {len(mail.outbox)}")

        # Student email
        student_email = None
        org_email = None
        for msg in mail.outbox:
            if "student@test.com" in msg.to:
                student_email = msg
            if "emp@test.com" in msg.to:
                org_email = msg

        self.assertIsNotNone(student_email, "Student email not found in outbox")
        self.assertIn("přihláška na praxi byla zrušena", student_email.subject)
        self.assertIn(reason, student_email.body)
        self.assertIn("student@test.com", student_email.to)

        self.assertIsNotNone(org_email, "Org email not found in outbox")
        self.assertIn("přihláška studenta na praxi byla zrušena", org_email.subject.lower())
        self.assertIn(reason, org_email.body)
        self.assertIn("emp@test.com", org_email.to)

    # --- M-M4-3: DocumentHelper logs error when all templates missing ---

    @override_settings(MEDIA_ROOT="/nonexistent/path")
    def test_assign_default_documents_logs_error_when_none_created(self):
        """If all three default document templates are missing, log an error."""
        from unittest.mock import patch

        sp = self._create_student_practice()

        with patch.object(DocumentHelper, "create_default_document", return_value=None):
            with self.assertLogs("student_practices.models", level="ERROR") as log_cm:
                DocumentHelper.assign_default_documents(sp)

        self.assertTrue(
            any("No default documents could be created" in msg for msg in log_cm.output),
            f"Expected error log about missing documents, got: {log_cm.output}",
        )
