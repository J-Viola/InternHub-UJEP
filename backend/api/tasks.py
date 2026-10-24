from celery import shared_task
from django.core.cache import cache

from api.export_service import ExportService
from student_practices.models import StudentPractice


@shared_task(name="export_data_async")
def export_data_async(export_id: str, filters: dict, fmt: str, user_id: int | None = None):
    """
    Celery task pro asynchronní export dat.

    Args:
        export_id: Unikátní ID exportu (pro sledování progressu).
        filters: Filtrovací parametry (year, workflow_state, subject_id).
        fmt: "xlsx" nebo "csv".
        user_id: PK uživatele, který export založil — scoping + notifikace
            o dokončení (garant/profesor → jen praxe svého departmentu).
    """
    try:
        # Ownership marker (MAJOR-3): založení exportu vždy doloží žadatele,
        # aby status/download guard fail-closed fungoval i pro task volané
        # mimo DataExportView. TTL > TTL dat (3600) jako ve view (A2).
        if user_id is not None:
            cache.set(f"export_{export_id}_user_id", user_id, timeout=7200)

        # Sestav queryset dle filtrů (shodně s DataExportView) + role-based scoping
        qs = StudentPractice.objects.filter(is_cancelled=False)

        # Fail-closed (BE-003): scope se aplikuje VŽDY — neznámý/žádný
        # žadatel ani prázdný rozsah nikdy neznamenají neomezený export.
        from users.models import User

        user = User.objects.filter(pk=user_id).first() if user_id is not None else None
        dept_ids, employer, owner_user = ExportService.get_scope_filters(user)
        qs = ExportService.apply_scope(qs, dept_ids, employer, owner_user)

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

        # notifikace o dokončení žádajícímu uživateli (verb EXPORT_READY).
        # Export nemá DB model → export_record=None (target se vynechá);
        # download URL se předává do Notification.url i message.
        if user_id is not None:
            from notifications.services import NotificationService

            from users.models import User

            user = User.objects.filter(pk=user_id).first()
            if user:
                NotificationService.notify_export_ready(user, None, download_url=f"/api/export/download/{export_id}/")
    except Exception as e:
        cache.set(f"export_{export_id}_status", f"error: {str(e)}", timeout=3600)
