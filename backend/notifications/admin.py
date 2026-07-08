from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "recipient", "verb", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "verb"]
    search_fields = ["recipient__email", "verb", "message"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]
