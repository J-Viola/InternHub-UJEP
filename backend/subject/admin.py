from django.contrib import admin

from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "subject_code",
        "subject_name",
        "department",
        "hours_required",
        "min_hours",
        "subject_manager",
    )
    list_filter = ("department", "min_hours")
    search_fields = ("subject_code", "subject_name")
