"""
Management command to prune old ActionLog entries.

Usage:
    python manage.py cleanup_old_action_logs --days 365
    python manage.py cleanup_old_action_logs --days 90 --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import ActionLog


class Command(BaseCommand):
    help = "Deletes ActionLog entries older than a specified number of days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Delete entries older than this many days (default: 365)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff_date = timezone.now() - timedelta(days=days)

        queryset = ActionLog.objects.filter(action_date__lt=cutoff_date)
        count = queryset.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would delete {count} ActionLog entries older than {days} days "
                    f"(before {cutoff_date.strftime('%Y-%m-%d')})."
                )
            )
        else:
            deleted, _ = queryset.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted} ActionLog entries older than {days} days " f"(before {cutoff_date.strftime('%Y-%m-%d')})."
                )
            )
