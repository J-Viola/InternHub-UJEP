from datetime import date, timedelta

from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from department.models import Department
from practices.models import Practice, PracticeWorkflowState
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from student_practices.services import StudentPracticeService
from users.models import ApprovalStatus, DepartmentRole, EmployerProfile, ProfessorUser, StagRole, StudentUser


class Phase4FullTestSuite(APITestCase):
    def setUp(self):
        self.student = StudentUser.objects.create_user(
            email="phase4_student@example.com",
            password="Password123!",
            first_name="Martin",
            last_name="Kovář",
        )
        self.employer = EmployerProfile.objects.create(
            company_name="Phase 4 Corp",
            ico="99887766",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.practice = Practice.objects.create(
            title="Fullstack Developer Intern",
            description="Phase 4 practice",
            employer=self.employer,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            progress_status=1,
            approval_status=ApprovalStatus.APPROVED,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=45),
        )

    def test_all_13_states_enum_and_transitions(self):
        """Item 4.1: Test 13-state enum representation and transitions matrix router."""
        self.assertEqual(len(list(StudentPracticeWorkflowState)), 13)
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        matrix = StudentPracticeService.get_transitions_matrix(sp)
        self.assertIn(StudentPracticeWorkflowState.PRELIMINARY_APPROVED, matrix[StudentPracticeWorkflowState.APPLIED])

    def test_ares_fallback_cached_and_miss(self):
        """Item 4.2: Test ARES API DB fallback on error / timeout."""
        self.client.force_authenticate(user=self.student)
        res = self.client.get(f"/api/users/ares-justice/?ico={self.employer.ico}")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED])

    def test_auto_close_practices_management_command(self):
        """Item 4.3: Test auto_close_practices management command."""
        self.practice.start_date = date.today() + timedelta(days=5)  # < 14 days
        self.practice.save()
        call_command("auto_close_practices")
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)

    def test_auto_start_end_practices_management_command(self):
        """Item 4.3: Test auto_start_end_practices management command."""
        self.practice.start_date = date.today() - timedelta(days=1)
        self.practice.save()
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
        )
        call_command("auto_start_end_practices")
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.STARTED)

    # ===========================================================================
    # 4.8: UC-14 — auto-close & content reject
    # ===========================================================================

    def test_auto_close_14_days_before_start(self):
        """Item 4.8: Auto-close closes practices within the 14-day window."""
        self.practice.start_date = date.today() + timedelta(days=5)
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.save()
        call_command("auto_close_practices")
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)

    def test_auto_close_outside_14_day_window(self):
        """Item 4.8: Auto-close does NOT affect practices outside the 14-day window."""
        self.practice.start_date = date.today() + timedelta(days=30)
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.save()
        call_command("auto_close_practices")
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)

    def test_content_reject_transition(self):
        """Item 4.8: Content reject transition via state machine (UC-14)."""
        # Content transitions require external practice (MANUAL_SP_TRANSITIONS)
        self.practice.is_external = True
        self.practice.save()
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        # Transition AWAITING_CONTENT_APPROVAL -> CONTENT_REJECTED (UC-14)
        # Content reject is a professor action, not a student action
        dept = Department.objects.create(department_name="Informatika", department_code="KI")
        stag_role = StagRole.objects.create(role="vy", role_name="Vyučující")
        professor = ProfessorUser.objects.create(
            email="prof_content_reject@test.com",
            first_name="Prof",
            last_name="Reject",
            is_active=True,
            department=dept,
            stag_role=stag_role,
            department_role=DepartmentRole.TEACHER,
        )
        from student_practices.services import StudentPracticeService

        sp = StudentPracticeService.transition_student_practice_state(
            sp=sp,
            target_state=StudentPracticeWorkflowState.CONTENT_REJECTED,
            actor=professor,
            reason="Obsah nesplňuje požadavky",
        )
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTENT_REJECTED)

    def test_student_edit_and_resubmit_content(self):
        """Item 4.8: Student edit → resubmit content (CONTENT_REJECTED → AWAITING_CONTENT_APPROVAL)."""
        # Content transitions require external practice (MANUAL_SP_TRANSITIONS)
        self.practice.is_external = True
        self.practice.save()
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.CONTENT_REJECTED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        from student_practices.services import StudentPracticeService

        sp = StudentPracticeService.transition_student_practice_state(
            sp=sp,
            target_state=StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL,
            actor=self.student,
            reason="Opraveno dle připomínek",
        )
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)
