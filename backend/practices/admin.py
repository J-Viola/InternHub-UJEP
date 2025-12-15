from django.contrib import admin

from .models import Practice


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "subject", "start_date", "end_date", "approval_status", "is_active")
    list_filter = ("approval_status", "is_active", "start_date", "employer")
    search_fields = ("title", "description", "employer__company_name")
    date_hierarchy = "start_date"
    list_select_related = ("employer", "subject")
