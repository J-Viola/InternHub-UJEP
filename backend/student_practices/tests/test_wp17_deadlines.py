"""deadline výstrahy — urgence před zahájením + alert na zápočet."""

from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from notifications.models import Notification

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class DeadlineUrgencyTests(TestCase):
    """urgence ve 14/7/2 dnech, právě jednou; ve CONTRACTED ne; po 14 dnech."""

    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="student@dl.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="org@dl.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="DL Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.garant = ProfessorUser.objects.create_user(
            email="garant@dl.test",
            password="password123",
            first_name="Alice",
            last_name="Garant",
            is_active=True,
            department=self.department,
            is_garant_praxe=True,
        )

        self.practice = Practice.objects.create(
            title="Deadline praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=44),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

    def _sp(self, state, start_delta_days):
        from django.utils import timezone

        student = StudentUser.objects.create(
            email=f"student-{timezone.now().timestamp()}@dl.test",
            first_name="Jan",
            last_name="Novák",
            is_active=True,
        )
        practice = Practice.objects.create(
            title=f"Deadline praxe {timezone.now().timestamp()}",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today() + timedelta(days=start_delta_days),
            end_date=date.today() + timedelta(days=start_delta_days + 30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        return StudentPractice.objects.create(
            user=student,
            practice=practice,
            start_date=date.today() + timedelta(days=start_delta_days),
            end_date=date.today() + timedelta(days=start_delta_days + 30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
        )

    def test_urgency_sent_at_14_7_2_days_and_exactly_once(self):
        """Urgence vzniká pro start za 14/7/2 dny a právě jednou (idempotence)."""
        sp14 = self._sp(StudentPracticeWorkflowState.APPLIED, 14)
        sp7 = self._sp(StudentPracticeWorkflowState.APPLIED, 7)
        sp2 = self._sp(StudentPracticeWorkflowState.APPLIED, 2)

        call_command("notify_practice_deadlines")
        sp14.refresh_from_db()
        sp7.refresh_from_db()
        sp2.refresh_from_db()

        self.assertEqual(sp14.urgency_level, 1)
        self.assertEqual(sp7.urgency_level, 2)
        self.assertEqual(sp2.urgency_level, 3)
        self.assertIsNotNone(sp14.last_urgency_sent_at)

        notifications = Notification.objects.filter(verb="PRACTICE_START_URGENCY")
        self.assertEqual(notifications.count(), 3)

        # Druhé spuštění → žádné duplicity
        call_command("notify_practice_deadlines")
        self.assertEqual(Notification.objects.filter(verb="PRACTICE_START_URGENCY").count(), 3)

    def test_no_urgency_for_contracted(self):
        """Praxe ve stavu CONTRACTED nedostává urgenci (: „mimo stav CONTRACTED")."""
        sp = self._sp(StudentPracticeWorkflowState.CONTRACTED, 2)
        call_command("notify_practice_deadlines")
        sp.refresh_from_db()
        self.assertEqual(sp.urgency_level, 0)
        self.assertFalse(Notification.objects.filter(verb="PRACTICE_START_URGENCY", object_id=sp.student_practice_id).exists())

    def test_no_urgency_when_start_far_away(self):
        """Start za >14 dní → žádná urgence."""
        sp = self._sp(StudentPracticeWorkflowState.APPLIED, 30)
        call_command("notify_practice_deadlines")
        sp.refresh_from_db()
        self.assertEqual(sp.urgency_level, 0)

    def test_credit_alert_after_14_days_ended(self):
        """ENDED déle než PRACTICE_CREDIT_ALERT_DAYS → e-mail+in-app garantovi (1×)."""
        sp = self._sp(StudentPracticeWorkflowState.ENDED, -30)
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=timezone.now() - timedelta(days=15))

        call_command("notify_practice_deadlines")
        notifs = Notification.objects.filter(verb="CREDIT_ALERT_GARANT", object_id=sp.student_practice_id)
        self.assertEqual(notifs.count(), 1)
        self.assertEqual(notifs.first().recipient, self.garant)

        # Druhé spuštění → žádná duplicita
        call_command("notify_practice_deadlines")
        self.assertEqual(Notification.objects.filter(verb="CREDIT_ALERT_GARANT", object_id=sp.student_practice_id).count(), 1)

    def test_no_credit_alert_before_threshold(self):
        """ENDED krátce (< 14 dní) → žádný alert."""
        sp = self._sp(StudentPracticeWorkflowState.ENDED, -30)
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=timezone.now() - timedelta(days=5))
        call_command("notify_practice_deadlines")
        self.assertFalse(Notification.objects.filter(verb="CREDIT_ALERT_GARANT", object_id=sp.student_practice_id).exists())
