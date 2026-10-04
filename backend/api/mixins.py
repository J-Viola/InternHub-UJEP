"""
Sdílené abstraktní Django model mixiny pro celý projekt.
"""

from django.db import models


class CancellationMixin(models.Model):
    """
    Abstraktní mixin přidávající storno-bloček na entity Practice a StudentPractice.

    Důvod existence:
    - Zadavatel explicitně vyžaduje auditní stopu storna (kdy, kdo, proč).
    - „Stornováno" je flag, nikoli stav — zamrazí záznam mimo standardní stavový automat.
    - Konzistentní pojmenování na obou entitách (DRY).
    """

    is_cancelled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Příznak, zda byl záznam stornován. Idempotentní — nelze vrátit zpět.",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp okamžiku stornování.",
    )
    cancelled_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Uživatel, který storno provedl.",
    )
    cancellation_reason = models.TextField(
        blank=True,
        default="",
        help_text="Povinný důvod storna (zadáván uživatelem v UI).",
    )
    cancellation_resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp vyřešení storna (pokud bylo storno vyřešeno).",
    )

    class Meta:
        abstract = True
