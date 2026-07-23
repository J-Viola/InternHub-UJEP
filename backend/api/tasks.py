from celery import shared_task
from django.core.cache import cache

from api.export_service import ExportService
from student_practices.models import StudentPractice


@shared_task(name="export_data_async")
def export_data_async(export_id: str, filters: dict, fmt: str):
    """
    Celery task pro asynchronní export dat.

    Args:
        export_id: Unikátní ID exportu (pro sledování progressu).
        filters: Filtrovací parametry (year, workflow_state, subject_id).
        fmt: "xlsx" nebo "csv".
    """
    try:
        # Sestav queryset dle filtrů (shodně s DataExportView)
        qs = StudentPractice.objects.filter(is_cancelled=False)
        if filters.get("year"):
            qs = qs.filter(year=filters["year"])
        if filters.get("workflow_state") is not None:
            qs = qs.filter(workflow_state=filters["workflow_state"])
        if filters.get("subject_id"):
            qs = qs.filter(practice__subject_id=filters["subject_id"])

        if fmt == "csv":
            result = ExportService.generate_csv(qs)
        else:
            result = ExportService.generate_xlsx(qs)

        # Ulož výsledek do cache po dobu 1 hodiny
        cache.set(f"export_{export_id}", result, timeout=3600)
        cache.set(f"export_{export_id}_fmt", fmt, timeout=3600)
        cache.set(f"export_{export_id}_status", "completed", timeout=3600)
    except Exception as e:
        cache.set(f"export_{export_id}_status", f"error: {str(e)}", timeout=3600)
