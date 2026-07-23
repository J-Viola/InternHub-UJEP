from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Setup Celery Beat periodic tasks in database"

    def handle(self, *args, **options):
        # Auto-close practices: daily at 2:00 AM
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        PeriodicTask.objects.get_or_create(
            name="Auto-close practices",
            defaults={
                "task": "auto_close_practices",
                "crontab": schedule,
                "enabled": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Auto-close practice task created."))

        # Auto-start/end practices: daily at 3:00 AM
        schedule2, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="3",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        PeriodicTask.objects.get_or_create(
            name="Auto-start/end practices",
            defaults={
                "task": "auto_start_end_practices",
                "crontab": schedule2,
                "enabled": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Auto-start/end practice task created."))
