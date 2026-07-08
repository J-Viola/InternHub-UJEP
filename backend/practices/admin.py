from django.contrib import admin

from .models import ExternalEmployerInfo, Practice


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "employer",
        "subject",
        "start_date",
        "end_date",
        "approval_status",
        "is_active",
    )
    list_filter = ("approval_status", "is_active", "start_date", "employer")
    search_fields = ("title", "description", "employer__company_name")
    date_hierarchy = "start_date"
    list_select_related = ("employer", "subject")


@admin.register(ExternalEmployerInfo)
class ExternalEmployerInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "ico", "contact_name", "contact_email", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "ico", "contact_name", "contact_email")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
