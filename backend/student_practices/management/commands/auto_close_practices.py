from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from notifications.models import NotificationType
from notifications.services import NotificationService

from practices.models import ApplicationClosureReason, Practice, PracticeWorkflowState
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from users.action_log import ActionLogService
from users.constants import ActionLogType


class Command(BaseCommand):
    help = (
        "Auto-close practice offers v den zahájení (start_date <= today) "
        "nebo při naplněné kapacitě — zapisuje closed_reason a closed_for_applications_at."
    )

    def handle(self, *args, **options):
        today = date.today()
        closed_count = 0

        # Auto-close dle data zahájení: nastane-li datum zahájení praxe
        # (start_date <= today) → CLOSED_FOR_APPLICATIONS + closed_reason=TIME.
        open_practices = Practice.objects.filter(
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            start_date__isnull=False,
            start_date__lte=today,
            is_cancelled=False,
        )

        for practice in open_practices:
            with transaction.atomic():
                practice = Practice.objects.select_for_update().get(pk=practice.pk)
                if practice.workflow_state == PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                    practice.workflow_state = PracticeWorkflowState.CLOSED_FOR_APPLICATIONS
                    practice.closed_reason = ApplicationClosureReason.TIME
                    practice.closed_for_applications_at = timezone.now()
                    practice.save(update_fields=["workflow_state", "closed_reason", "closed_for_applications_at", "updated_at"])
                    closed_count += 1

                    ActionLogService.log(
                        user=None,
                        action_type=ActionLogType.STATE_TRANSITION,
                        object_type="Practice",
                        object_id=practice.practice_id,
                        description=f"Auto-close inzerátu ID {practice.practice_id} (datum zahájení {practice.start_date}, TIME)",
                    )

                    if practice.contact_user:
                        NotificationService.create_notification(
                            recipient=practice.contact_user,
                            verb="PRACTICE_AUTO_CLOSED",
                            message=f"Nabídka praxe '{practice.title}' byla automaticky uzavřena (v den zahájení).",
                            target=practice,
                            notification_type=NotificationType.INFO,
                        )

        # Check capacity-based auto-close: closed_reason=CAPACITY
        for practice in Practice.objects.filter(
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            is_cancelled=False,
        ):
            approved_count = StudentPractice.objects.filter(
                practice=practice,
                workflow_state__in=[
                    StudentPracticeWorkflowState.CONTRACTED,
                    StudentPracticeWorkflowState.STARTED,
                    StudentPracticeWorkflowState.ENDED,
                    StudentPracticeWorkflowState.COMPLETED,
                ],
            ).count()
            if practice.available_positions is not None and approved_count >= practice.available_positions:
                with transaction.atomic():
                    practice = Practice.objects.select_for_update().get(pk=practice.pk)
                    if practice.workflow_state == PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                        practice.workflow_state = PracticeWorkflowState.CLOSED_FOR_APPLICATIONS
                        practice.closed_reason = ApplicationClosureReason.CAPACITY
                        practice.closed_for_applications_at = timezone.now()
                        practice.save(update_fields=["workflow_state", "closed_reason", "closed_for_applications_at", "updated_at"])
                        closed_count += 1

                        ActionLogService.log(
                            user=None,
                            action_type=ActionLogType.STATE_TRANSITION,
                            object_type="Practice",
                            object_id=practice.practice_id,
                            description=f"Auto-close inzerátu ID {practice.practice_id} (naplněna kapacita, CAPACITY)",
                        )

                        if practice.contact_user:
                            NotificationService.create_notification(
                                recipient=practice.contact_user,
                                verb="PRACTICE_AUTO_CLOSED",
                                message=f"Nabídka praxe '{practice.title}' byla automaticky uzavřena (naplněna kapacita).",
                                target=practice,
                                notification_type=NotificationType.INFO,
                            )

        self.stdout.write(self.style.SUCCESS(f"Úspěšně uzavřeno {closed_count} inzerátů."))
