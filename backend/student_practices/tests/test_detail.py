"""
Tests for StudentPractice detail, history timeline, withdraw.

Covers:
- GET history endpoint returns ActionLog entries
- GET history endpoint — access only for participants
- POST withdraw — success (APPLIED state)
- POST withdraw — wrong state (not APPLIED/PRELIMINARY_APPROVED)
- POST withdraw — unauthorized user (not the owner)
"""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    StudentPractice,
    StudentPracticeWorkflowState,
)
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    StudentUser,
)


class StudentPracticeDetailTests(TestCase):
    """Detail přihlášky, timeline historie, withdraw."""

    def setUp(self):
        self.client = APIClient()

        # Users
        self.student = StudentUser.objects.create(
            email="student@detail.test",
            first_name="Jan",
            last_name="Novák",
            is_active=True,
        )
        self.other_student = StudentUser.objects.create(
            email="other@detail.test",
            first_name="Petr",
            last_name="Svoboda",
            is_active=True,
        )

        # Employer
        self.org_user = OrganizationUser.objects.create(
            email="org@detail.test",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Detail Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Practice
        self.practice = Practice.objects.create(
            title="Test Developer",
            employer=self.employer,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=65),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            is_active=True,
        )

        # StudentPractice in APPLIED state
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
        )

        # Create some ActionLog entries for the SP
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

        # URLs
        self.history_url = f"/api/student-practices/{self.sp.student_practice_id}/history/"
        self.withdraw_url = f"/api/student-practices/{self.sp.student_practice_id}/withdraw/"

    # ----- HISTORY TESTS -----

    def test_history_returns_action_logs(self):
        """GET history endpoint returns ActionLog entries for the SP."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)
        # Check structure
        self.assertIn("action_type", response.data[0])
        self.assertIn("action_description", response.data[0])
        self.assertIn("action_date", response.data[0])

    def test_history_access_denied_for_non_participant(self):
        """GET history — non-participant student gets 403."""
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----- WITHDRAW TESTS -----

    def test_withdraw_success(self):
        """POST withdraw — student successfully withdraws APPLIED application."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.withdraw_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.REJECTED)

    def test_withdraw_wrong_state(self):
        """POST withdraw — wrong state (not APPLIED/PRELIMINARY_APPROVED) returns 400."""
        # Change state to CONTRACTED
        self.sp.workflow_state = StudentPracticeWorkflowState.CONTRACTED
        self.sp.save()

        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.withdraw_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)

    def test_withdraw_unauthorized_user(self):
        """POST withdraw — another student cannot withdraw."""
        self.client.force_authenticate(user=self.other_student)
        response = self.client.post(self.withdraw_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.APPLIED)

    def test_card_view_is_logged_once_per_hour(self):
        """F-3: opakované otevření karty nezahlcuje historii."""
        from users.models import ActionLog

        card_url = f"/api/student-practices/{self.sp.student_practice_id}"
        filters = {
            "user": self.student,
            "action_type": ActionLogType.VIEW,
            "object_type": "StudentPractice",
            "object_id": self.sp.student_practice_id,
            "action_description__startswith": "Zobrazení karty",
        }
        self.client.force_authenticate(user=self.student)
        for _ in range(3):
            self.assertEqual(self.client.get(card_url).status_code, status.HTTP_200_OK)
        self.assertEqual(ActionLog.objects.filter(**filters).count(), 1)

        ActionLog.objects.filter(**filters).update(action_date=timezone.now() - timedelta(hours=2))
        self.client.get(card_url)
        self.assertEqual(ActionLog.objects.filter(**filters).count(), 2)
