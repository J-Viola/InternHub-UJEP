from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from api.dashboard_service import DashboardService
from practices.models import ApprovalStatus, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from users.constants import ActionLogType
from users.models import ActionLog

from .test_export_rf21b import ExportRF21BTests


class DashboardRiskTests(ExportRF21BTests):
    def test_approval_stall_uses_last_transition_and_sets_risk_type(self):
        old_transition = timezone.now() - timedelta(days=10)
        self.sp_a.workflow_state = StudentPracticeWorkflowState.APPLIED
        self.sp_a.save(update_fields=["workflow_state"])
        ActionLog.objects.create(
            object_type="StudentPractice",
            object_id=self.sp_a.pk,
            action_type=ActionLogType.STATE_TRANSITION,
            action_description="APPLIED -> APPLIED",
            action_date=old_transition,
        )

        result = DashboardService.get_stats_for_user(self._admin())
        item = next(item for item in result["at_risk_items"] if item["student_practice_id"] == self.sp_a.pk)
        self.assertEqual(item["risk_type"], "APPROVAL_STALLED")
        self.assertTrue(item["risk_reason"])

    def test_ended_without_credit_and_overdue_started_have_distinct_types(self):
        stale = timezone.now() - timedelta(days=20)
        self.sp_a.workflow_state = StudentPracticeWorkflowState.ENDED
        self.sp_a.save(update_fields=["workflow_state"])
        StudentPractice.objects.filter(pk=self.sp_a.pk).update(updated_at=timezone.now())
        ActionLog.objects.create(
            object_type="StudentPractice",
            object_id=self.sp_a.pk,
            action_type=ActionLogType.STATE_TRANSITION,
            action_description="STARTED -> ENDED",
            action_date=stale,
        )
        self.sp_b.workflow_state = StudentPracticeWorkflowState.STARTED
        self.sp_b.save(update_fields=["workflow_state"])
        stats = DashboardService.get_stats_for_user(self._admin())
        type_by_id = {item["student_practice_id"]: item["risk_type"] for item in stats["at_risk_items"]}
        self.assertEqual(type_by_id[self.sp_a.pk], "ENDED_NO_CREDIT")
        self.assertEqual(type_by_id[self.sp_b.pk], "OVERDUE_END")

    def test_risk_count_is_exact_capped_and_query_count_does_not_scale(self):
        user = self._admin()
        now = timezone.now()

        def add_risks(count):
            test_practices = [self._practice(self.employer_a, f"Risk practice {i}") for i in range(count)]
            practices = [
                StudentPractice(
                    user=self.student_a,
                    practice=practice,
                    start_date=practice.start_date,
                    end_date=practice.end_date,
                    approval_status=ApprovalStatus.APPROVED,
                    progress_status=ProgressStatus.NOT_STARTED,
                    workflow_state=StudentPracticeWorkflowState.ENDED.value,
                    year=2025,
                )
                for practice in test_practices
            ]
            StudentPractice.objects.bulk_create(practices)
            ActionLog.objects.bulk_create(
                [
                    ActionLog(
                        object_type="StudentPractice",
                        object_id=sp.pk,
                        action_type=ActionLogType.STATE_TRANSITION,
                        action_description="STARTED -> ENDED",
                        action_date=now - timedelta(days=20),
                    )
                    for sp in practices
                ]
            )

        add_risks(5)
        with CaptureQueriesContext(connection) as small_queries:
            small_result = DashboardService.get_stats_for_user(user)

        add_risks(55)
        with CaptureQueriesContext(connection) as large_queries:
            large_result = DashboardService.get_stats_for_user(user)

        self.assertEqual(len(small_result["at_risk_items"]), 5)
        self.assertEqual(len(large_result["at_risk_items"]), 50)
        self.assertEqual(large_result["at_risk_count"], 60)
        self.assertEqual(len(small_queries), len(large_queries))

    @staticmethod
    def _admin():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_superuser(email="rf21b-admin@example.test", password="test-only")
