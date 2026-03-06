from django.contrib import admin

from .models import EmployerInvitation, StudentPractice, UploadedDocument


@admin.register(StudentPractice)
class StudentPracticeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "practice",
        "approval_status",
        "progress_status",
        "year",
        "hours_completed",
        "application_date",
    )
    list_filter = (
        "approval_status",
        "progress_status",
        "year",
        "practice__subject__department",
    )
    search_fields = ("user__email", "user__last_name", "practice__title")
    list_select_related = ("user", "practice")
    readonly_fields = ("contract_document", "content_document", "feedback_document")
    date_hierarchy = "application_date"


@admin.register(EmployerInvitation)
class EmployerInvitationAdmin(admin.ModelAdmin):
    list_display = ("user", "employer", "practice", "status", "submission_date")
    list_filter = ("status", "submission_date")
    search_fields = ("user__email", "employer__company_name", "practice__title")
    date_hierarchy = "submission_date"


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("document", "document_type", "uploaded_at")
    list_filter = ("document_type", "uploaded_at")
    search_fields = ("document",)
