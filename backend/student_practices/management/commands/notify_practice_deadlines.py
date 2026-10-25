from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from notifications.models import Notification, NotificationType
from notifications.services import NotificationService

from api.parameter_service import get_param
from student_practices.models import StudentPractice, StudentPracticeWorkflowState


class Command(BaseCommand):
    help = (
        "Deadline výstrahy: praxe mimo stav CONTRACTED se start_date "
        "za 14/7/2 dny (settings.PRACTICE_URGENCY_DAYS) → e-mail + in-app studentovi "
        "(idempotence přes last_urgency_sent_at/urgency_level); praxe ve stavu "
        "ENDED déle než PRACTICE_CREDIT_ALERT_DAYS bez přechodu do COMPLETED → "
        "e-mail + in-app garantovi."
    )

    def handle(self, *args, **options):
        today = date.today()
        urgency_days = get_param("PRACTICE_URGENCY_DAYS", [14, 7, 2])
        credit_alert_days = get_param("PRACTICE_CREDIT_ALERT_DAYS", 14)

        urgency_count = self._notify_start_urgent(today, urgency_days)
        credit_count = self._notify_credit_alert(credit_alert_days)

        self.stdout.write(self.style.SUCCESS(f"Urgence před zahájením: {urgency_count}, alert na zápočet: {credit_count}."))

    def _notify_start_urgent(self, today, urgency_days):
        """
        praxe mimo stav CONTRACTED, jejíž start_date nastane za 14/7/2 dny.

        Úroveň urgence = nejvyšší splněná prahová hodnota (start za 14 dní → level 1,
        za 7 → level 2, za 2 → level 3; za méně → level 3). Idempotence:
        ``urgency_level`` (0 = žádná) + ``last_urgency_sent_at`` — každá úroveň
        se odešle právě jednou.
        """
        sent = 0

        candidates = StudentPractice.objects.filter(
            is_cancelled=False,
        ).exclude(workflow_state=StudentPracticeWorkflowState.CONTRACTED)

        for sp in candidates:
            practice = sp.practice
            if practice is None or practice.start_date is None:
                continue

            days_until = (practice.start_date - today).days
            if days_until < 0:
                continue  # praxe už začala — řeší jiné procesy (overdue / auto-start)

            # Nejvyšší splněná úroveň
            selected_level = 0
            for level, threshold in enumerate(urgency_days, start=1):
                if days_until <= threshold:
                    selected_level = level
            if selected_level == 0:
                continue  # start_date příliš daleko

            if sp.urgency_level >= selected_level:
                continue  # tato úroveň už byla odeslána

            with transaction.atomic():
                sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
                if sp.urgency_level >= selected_level:
                    continue
                sp.urgency_level = selected_level
                sp.last_urgency_sent_at = timezone.now()
                sp.save(update_fields=["urgency_level", "last_urgency_sent_at"])

                if sp.user:
                    title = practice.title or "N/A"
                    NotificationService.create_notification(
                        recipient=sp.user,
                        verb="PRACTICE_START_URGENCY",
                        message=(
                            f"Praxe '{title}' začíná za {days_until} dní a stále není "
                            f"zasmluvněna. Prosím o urychlené vyřešení v systému InternHub."
                        ),
                        target=sp,
                        notification_type=NotificationType.WARNING,
                        send_email=True,  # e-mail + in-app
                    )
                    sent += 1

        return sent

    def _notify_credit_alert(self, credit_alert_days):
        """
        praxe ve stavu ENDED déle než PRACTICE_CREDIT_ALERT_DAYS bez přechodu
        do COMPLETED → e-mail + in-app garantovi.

        Idempotence: existuje-li již notifikace CREDIT_ALERT_GARANT pro danou praxi.
        """
        sent = 0
        sp_content_type = ContentType.objects.get_for_model(StudentPractice)
        threshold = timezone.now() - timedelta(days=credit_alert_days)

        candidates = StudentPractice.objects.filter(
            workflow_state=StudentPracticeWorkflowState.ENDED,
            is_cancelled=False,
            updated_at__lte=threshold,
        )

        for sp in candidates:
            already_sent = Notification.objects.filter(
                verb="CREDIT_ALERT_GARANT",
                content_type=sp_content_type,
                object_id=sp.student_practice_id,
            ).exists()
            if already_sent:
                continue

            recipients = NotificationService.resolve_garant_recipients(sp)
            if not recipients:
                continue

            with transaction.atomic():
                sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
                if sp.workflow_state != StudentPracticeWorkflowState.ENDED:
                    continue
                practice_title = sp.practice.title if sp.practice else "N/A"
                student_name = sp.user.full_name if sp.user else "N/A"
                message = (
                    f"Praxe '{practice_title}' studenta {student_name} je ukončena déle "
                    f"než {credit_alert_days} dní bez udělení zápočtu. "
                    f"Prosím o dokončení v systému InternHub."
                )
                for recipient in recipients:
                    NotificationService.create_notification(
                        recipient=recipient,
                        verb="CREDIT_ALERT_GARANT",
                        message=message,
                        target=sp,
                        notification_type=NotificationType.WARNING,
                        send_email=True,  # e-mail + in-app
                    )
                sent += 1

        return sent
