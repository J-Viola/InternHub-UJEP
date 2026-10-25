from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from notifications.services import NotificationService

from api.parameter_service import get_param
from student_practices.models import StudentPractice, StudentPracticeWorkflowState


class Command(BaseCommand):
    help = (
        "Eskalace SMLOUVA_PO_TERMINU: pro každou praxi ve stavu "
        "AWAITING_CONTRACT déle než settings.PRACTICE_CONTRACT_OVERDUE_DAYS odešle "
        "JEDNOU notifikaci garantovi (idempotence přes contract_overdue_notified_at)."
    )

    def handle(self, *args, **options):
        overdue_days = get_param("PRACTICE_CONTRACT_OVERDUE_DAYS", 7)
        notified_count = 0

        # Rychlá předfiltrace: AWAITING_CONTRACT + updated_at starší než práh.
        # Přesný výpočet stáří řeší property contract_overdue (ActionLog / updated_at).
        threshold = timezone.now() - timedelta(days=overdue_days)
        candidates = StudentPractice.objects.filter(
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
            is_cancelled=False,
            contract_overdue_notified_at__isnull=True,
            updated_at__lte=threshold,
        )

        for sp in candidates:
            with transaction.atomic():
                sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
                if sp.contract_overdue and sp.contract_overdue_notified_at is None:
                    # Idempotence: flag se nastaví vždy, ať už mají garanti e-mail či ne
                    # (retry by bez příjemců nic nepřidal).
                    sp.contract_overdue_notified_at = timezone.now()
                    sp.save(update_fields=["contract_overdue_notified_at"])
                    NotificationService.notify_garant_contract_overdue(sp)
                    notified_count += 1

        self.stdout.write(self.style.SUCCESS(f"Odesláno {notified_count} notifikací o prodlení se zasmluvněním."))
