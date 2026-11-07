"""(SMLOUVA_PO_TERMINU): contract_overdue flag + eskalační command."""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from notifications.models import Notification
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from student_practices.serializers import ListStudentPracticeSerializer
from subject.models import Subject
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class ContractOverdueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="student@ov.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="org@ov.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Ov Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.garant = ProfessorUser.objects.create_user(
            email="garant@ov.test",
            password="password123",
            first_name="Alice",
            last_name="Garant",
            is_active=True,
            department=self.department,
            is_garant_praxe=True,
        )
        self.practice = Practice.objects.create(
            title="Overdue praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

    def _sp_in_awaiting_contract(self):
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )
        return sp

    def _log_awaiting_contract_transition(self, sp, when):
        ActionLogService.log(
            user=None,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Změna stavu přihlášky ID {sp.student_practice_id}: PRELIMINARY_APPROVED -> AWAITING_CONTRACT (bez důvodu)",
        )
        from users.models import ActionLog

        ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type=ActionLogType.STATE_TRANSITION,
        ).update(action_date=when)

    def test_contract_overdue_flag_true_after_threshold(self):
        """Ve stavu AWAITING_CONTRACT déle než PRACTICE_CONTRACT_OVERDUE_DAYS → True."""
        sp = self._sp_in_awaiting_contract()
        self._log_awaiting_contract_transition(sp, timezone.now() - timedelta(days=8))

        with patch("django.utils.timezone.now", return_value=timezone.now()):
            self.assertTrue(sp.contract_overdue)

    def test_contract_overdue_flag_false_before_threshold(self):
        """Ve stavu AWAITING_CONTRACT krátce → False."""
        sp = self._sp_in_awaiting_contract()
        self._log_awaiting_contract_transition(sp, timezone.now() - timedelta(days=2))

        with patch("django.utils.timezone.now", return_value=timezone.now()):
            self.assertFalse(sp.contract_overdue)

    def test_contract_overdue_false_outside_state(self):
        """Flag je False mimo stav AWAITING_CONTRACT."""
        sp = self._sp_in_awaiting_contract()
        sp.workflow_state = StudentPracticeWorkflowState.CONTRACTED
        sp.save()
        self.assertFalse(sp.contract_overdue)

    def test_list_serializer_exposes_contract_overdue(self):
        """List serializer vrací contract_overdue (bool)."""
        sp = self._sp_in_awaiting_contract()
        self._log_awaiting_contract_transition(sp, timezone.now() - timedelta(days=8))
        data = ListStudentPracticeSerializer(sp).data
        self.assertIn("contract_overdue", data)
        self.assertTrue(data["contract_overdue"])

    def test_notify_contract_overdue_command_sends_once(self):
        """Command vytvoří notifikaci garantovi právě jednou (idempotence)."""
        sp = self._sp_in_awaiting_contract()
        self._log_awaiting_contract_transition(sp, timezone.now() - timedelta(days=8))
        # Command předfiltruje kandidáty i přes updated_at — nastavme ho do minulosti
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=timezone.now() - timedelta(days=8))

        call_command("notify_contract_overdue")
        sp.refresh_from_db()
        self.assertIsNotNone(sp.contract_overdue_notified_at)
        notifs = Notification.objects.filter(verb="CONTRACT_OVERDUE", object_id=sp.student_practice_id)
        self.assertEqual(notifs.count(), 1)

        # Druhé spuštění → žádná duplicitní notifikace
        call_command("notify_contract_overdue")
        self.assertEqual(Notification.objects.filter(verb="CONTRACT_OVERDUE", object_id=sp.student_practice_id).count(), 1)

    def test_notify_contract_overdue_skips_fresh(self):
        """Command neeskaluje praxi, která není v prodlení."""
        sp = self._sp_in_awaiting_contract()
        self._log_awaiting_contract_transition(sp, timezone.now() - timedelta(days=2))

        call_command("notify_contract_overdue")
        sp.refresh_from_db()
        self.assertIsNone(sp.contract_overdue_notified_at)
        self.assertFalse(Notification.objects.filter(verb="CONTRACT_OVERDUE", object_id=sp.student_practice_id).exists())
