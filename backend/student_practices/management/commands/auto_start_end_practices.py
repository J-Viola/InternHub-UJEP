from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from notifications.models import NotificationType
from notifications.services import NotificationService

from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from users.action_log import ActionLogService
from users.constants import ActionLogType


class Command(BaseCommand):
    help = "Auto-starts and auto-ends student practices based on start/end dates."

    def handle(self, *args, **options):
        today = date.today()
        started_count = 0
        ended_count = 0

        # Auto-start: CONTRACTED -> STARTED
        contracted_sps = StudentPractice.objects.filter(
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
            practice__start_date__lte=today,
            is_cancelled=False,
        )

        for sp in contracted_sps:
            with transaction.atomic():
                sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
                if sp.workflow_state == StudentPracticeWorkflowState.CONTRACTED:
                    sp.workflow_state = StudentPracticeWorkflowState.STARTED
                    sp.save(update_fields=["workflow_state"])
                    started_count += 1

                    ActionLogService.log(
                        user=None,
                        action_type=ActionLogType.STATE_TRANSITION,
                        object_type="StudentPractice",
                        object_id=sp.student_practice_id,
                        description=f"Auto-start praxe ID {sp.student_practice_id} k datu {today}",
                    )

                    if sp.user:
                        NotificationService.create_notification(
                            recipient=sp.user,
                            verb="PRACTICE_STARTED",
                            message=f"Vaše praxe '{sp.practice.title}' byla dne {today} zahájena.",
                            target=sp,
                            notification_type=NotificationType.INFO,
                        )

        # Auto-end: STARTED -> ENDED
        started_sps = StudentPractice.objects.filter(
            workflow_state=StudentPracticeWorkflowState.STARTED,
            practice__end_date__lte=today,
            is_cancelled=False,
        )

        for sp in started_sps:
            with transaction.atomic():
                sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
                if sp.workflow_state == StudentPracticeWorkflowState.STARTED:
                    sp.workflow_state = StudentPracticeWorkflowState.ENDED
                    sp.save(update_fields=["workflow_state"])
                    ended_count += 1

                    ActionLogService.log(
                        user=None,
                        action_type=ActionLogType.STATE_TRANSITION,
                        object_type="StudentPractice",
                        object_id=sp.student_practice_id,
                        description=f"Auto-end praxe ID {sp.student_practice_id} k datu {today}",
                    )

                    if sp.user:
                        NotificationService.create_notification(
                            recipient=sp.user,
                            verb="PRACTICE_ENDED",
                            message=f"Vaše praxe '{sp.practice.title}' byla dne {today} ukončena.",
                            target=sp,
                            notification_type=NotificationType.INFO,
                        )

        self.stdout.write(self.style.SUCCESS(f"Auto-start: {started_count}, Auto-end: {ended_count}."))
