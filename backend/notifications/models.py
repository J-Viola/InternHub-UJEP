from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_enumfield import enum


class NotificationType(enum.Enum):
    """Visual severity — controls the colored badge on the notification bell."""

    INFO = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


class Notification(models.Model):
    """
    Single in-app notification delivered to a user's notification bell.

    Field roles
    -----------
    recipient
        The user who *receives* the notification (never ``None``).

    actor
        The user who *triggered* the notification.  ``None`` for system
        events (e.g. an automatic transition).

    verb
        A machine-readable event identifier such as ``"APPLICATION_REJECTED"``
        or ``"PRACTICE_APPROVED"``.  Used by the frontend for icon selection
        and by the admin list-filter.

    target
        A ``GenericForeignKey`` pointing to the domain object this notification
        is *about* — a ``Practice``, ``StudentPractice``, ``Document``, etc.
        ``None`` when there is no single associated entity.

    message
        Human-readable text shown to the user (currently Czech-only; i18n can
        be reintroduced later as ``message_cs`` / ``message_en`` if needed).

    notification_type
        Severity level (INFO / SUCCESS / WARNING / ERROR).

    is_read
        Whether the user has dismissed the notification.
    """

    recipient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User who receives this notification.",
    )
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions_performed",
        help_text="User who performed the action (null for system events).",
    )

    # --- Generic foreign key: target can be any model -----------------------
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    verb = models.CharField(
        max_length=255,
        help_text="Machine event name, e.g. PRACTICE_APPROVED, APPLICATION_REJECTED.",
    )
    message = models.TextField(
        help_text="Human-readable notification text (Czech).",
    )
    notification_type = enum.EnumField(NotificationType, default=NotificationType.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type.name}] {self.verb} → {self.recipient}"
