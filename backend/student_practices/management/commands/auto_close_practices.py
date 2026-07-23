from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from notifications.models import NotificationType
from notifications.services import NotificationService

from practices.models import Practice, PracticeWorkflowState
from users.action_log import ActionLogService
from users.constants import ActionLogType


class Command(BaseCommand):
    help = "Auto-closes practice offers 14 days before start_date (Item 2.9 / BDD AC-LI-04)."

    def handle(self, *args, **options):
        today = date.today()
        closed_count = 0

        open_practices = Practice.objects.filter(
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            start_date__isnull=False,
            is_cancelled=False,
        )

        for practice in open_practices:
            cutoff_date = practice.start_date - timedelta(days=14)
            if cutoff_date <= today:
                with transaction.atomic():
                    practice = Practice.objects.select_for_update().get(pk=practice.pk)
                    if practice.workflow_state == PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                        practice.workflow_state = PracticeWorkflowState.CLOSED_FOR_APPLICATIONS
                        practice.save(update_fields=["workflow_state", "updated_at"])
                        closed_count += 1

                        ActionLogService.log(
                            user=None,
                            action_type=ActionLogType.STATE_TRANSITION,
                            object_type="Practice",
                            object_id=practice.practice_id,
                            description=f"Auto-close inzerátu ID {practice.practice_id} (start_date {practice.start_date})",
                        )

                        if practice.contact_user:
                            NotificationService.create_notification(
                                recipient=practice.contact_user,
                                verb="PRACTICE_AUTO_CLOSED",
                                message=f"Nabídka praxe '{practice.title}' byla automaticky uzavřena (14 dní před začátkem).",
                                target=practice,
                                notification_type=NotificationType.INFO,
                            )

        self.stdout.write(self.style.SUCCESS(f"Úspěšně uzavřeno {closed_count} inzerátů."))
