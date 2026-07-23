from datetime import date, timedelta

from notifications.services import NotificationService
from rest_framework.test import APITestCase

from practices.models import Practice, PracticeWorkflowState
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from student_practices.services import StudentPracticeService
from users.models import ApprovalStatus, EmployerProfile, StudentUser


class Phase3Tests(APITestCase):
    def setUp(self):
        self.student = StudentUser.objects.create_user(
            email="student_p3@example.com",
            password="Password123!",
            first_name="Pavel",
            last_name="Dvořák",
        )
        self.employer = EmployerProfile.objects.create(
            company_name="Phase3 Corp",
            ico="87654321",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.practice = Practice.objects.create(
            title="Frontend Developer Intern",
            description="Phase 3 practice",
            employer=self.employer,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            progress_status=1,
            approval_status=ApprovalStatus.APPROVED,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=60),
        )
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.STARTED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

    def test_null_recipient_notification_safety(self):
        # Must return None and log warning without raising 500
        res = NotificationService.create_notification(
            recipient=None,
            verb="TEST_VERB",
            message="Test message",
        )
        self.assertIsNone(res)

    def test_cancellation_validation_on_completed(self):
        self.sp.workflow_state = StudentPracticeWorkflowState.COMPLETED
        self.sp.save()

        with self.assertRaises(ValueError):
            StudentPracticeService.cancel_student_practice(self.sp, self.student, "Zrušení z důvodu x")

    def test_cancellation_reason_required(self):
        with self.assertRaises(ValueError):
            StudentPracticeService.cancel_student_practice(self.sp, self.student, "")
