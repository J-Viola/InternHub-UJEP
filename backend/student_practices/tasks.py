from celery import shared_task
from django.core.management import call_command


@shared_task(name="auto_close_practices")
def auto_close_practices():
    """Auto-close practice offers 14 days before start_date"""
    call_command("auto_close_practices")


@shared_task(name="auto_start_end_practices")
def auto_start_end_practices():
    """Auto-start CONTRACTED→STARTED and auto-end STARTED→ENDED"""
    call_command("auto_start_end_practices")
