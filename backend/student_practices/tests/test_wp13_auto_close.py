"""auto_close trigger v den zahájení + closed_reason hodnoty."""

from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from department.models import Department
from practices.models import ApplicationClosureReason, Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser, StudentUser


class AutoCloseTriggerTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="student@ac.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="org@ac.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="AC Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

    def _practice(self, start_date, positions=5):
        return Practice.objects.create(
            title="AC praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=start_date,
            end_date=start_date + timedelta(days=30),
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=positions,
            is_active=True,
        )

    def test_auto_close_trigger_on_start_date(self):
        """Trigger = start_date <= today (V DEN zahájení) + closed_reason=TIME."""
        practice = self._practice(date.today())
        call_command("auto_close_practices")
        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)
        self.assertEqual(practice.closed_reason, ApplicationClosureReason.TIME)
        self.assertIsNotNone(practice.closed_for_applications_at)

    def test_auto_close_trigger_after_start_date(self):
        """Praxe, která už začala (start_date < today) → uzavřena s TIME."""
        practice = self._practice(date.today() - timedelta(days=1))
        call_command("auto_close_practices")
        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)
        self.assertEqual(practice.closed_reason, ApplicationClosureReason.TIME)

    def test_auto_close_not_triggered_before_start(self):
        """Praxe, která ještě nezačala (start_date > today) → zůstává otevřená."""
        practice = self._practice(date.today() + timedelta(days=1))
        call_command("auto_close_practices")
        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)
        self.assertIsNone(practice.closed_reason)

    def test_capacity_auto_close_sets_capacity_reason(self):
        """Kapacitní auto-close → closed_reason=CAPACITY."""
        practice = self._practice(date.today() + timedelta(days=10), positions=1)
        StudentPractice.objects.create(
            user=self.student,
            practice=practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
        )
        call_command("auto_close_practices")
        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)
        self.assertEqual(practice.closed_reason, ApplicationClosureReason.CAPACITY)
        self.assertIsNotNone(practice.closed_for_applications_at)
