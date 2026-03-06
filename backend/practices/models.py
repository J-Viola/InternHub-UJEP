from django.db import models
from django_enumfield import enum

from users.models import ApprovalStatus


class ProgressStatus(enum.Enum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class Practice(models.Model):
    practice_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(
        "users.EmployerProfile",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="practices",
    )
    subject = models.ForeignKey(
        "subject.Subject",
        models.PROTECT,
        blank=True,
        null=True,
        related_name="practices",
    )
    title = models.CharField(max_length=100, blank=True, default="", db_index=True)
    description = models.TextField(blank=True, default="")
    responsibilities = models.TextField(blank=True, default="")
    available_positions = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    progress_status = enum.EnumField(ProgressStatus, db_index=True)
    approval_status = enum.EnumField(ApprovalStatus, db_index=True)
    contact_user = models.ForeignKey(
        "users.OrganizationUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
    )
    is_active = models.BooleanField(blank=True, null=True, db_index=True)
    image_base64 = models.TextField(blank=True, default="")
    coefficient = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "practices"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or super().__str__()
