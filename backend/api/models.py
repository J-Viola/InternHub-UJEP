from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from solo.models import SingletonModel


def default_urgency_days():
    return [14, 7, 2]


def validate_urgency_days(value):
    """Neprázdný seznam kladných celých čísel, bez duplicit, seřazený sestupně."""
    if not isinstance(value, list) or not value:
        raise ValidationError("Zadejte neprázdný seznam dnů, např. [14, 7, 2].")
    if any(isinstance(day, bool) or not isinstance(day, int) or day < 1 for day in value):
        raise ValidationError("Všechny hodnoty musí být kladná celá čísla.")
    if len(set(value)) != len(value):
        raise ValidationError("Hodnoty se nesmí opakovat.")
    if value != sorted(value, reverse=True):
        raise ValidationError("Hodnoty musí být seřazeny sestupně (např. [14, 7, 2]).")


_DAYS_VALIDATORS = [MinValueValidator(1), MaxValueValidator(365)]
MB = 1024 * 1024


class SystemSettings(SingletonModel):
    """Systémové parametry (RNF-04, D-03) — jediný záznam, editace jen v Django adminu."""

    practice_urgency_days = models.JSONField(
        "Urgence před zahájením (dny)",
        default=default_urgency_days,
        validators=[validate_urgency_days],
        help_text="Počet dnů před zahájením praxe, kdy se studentovi odesílá urgentní upozornění. Seznam sestupně, např. [14, 7, 2].",
    )
    practice_credit_alert_days = models.PositiveSmallIntegerField(
        "Upozornění na zápočet (dny)",
        default=14,
        validators=_DAYS_VALIDATORS,
        help_text="Po kolika dnech od ukončení praxe bez zápočtu se upozorní garant (1–365 dní).",
    )
    practice_contract_overdue_days = models.PositiveSmallIntegerField(
        "Prodlení se zasmluvněním (dny)",
        default=7,
        validators=_DAYS_VALIDATORS,
        help_text="Po kolika dnech ve stavu „Čeká na zasmluvnění“ je praxe v prodlení (1–365 dní).",
    )
    practice_approval_stall_days = models.PositiveSmallIntegerField(
        "Zaseknuté schválení (dny)",
        default=7,
        validators=_DAYS_VALIDATORS,
        help_text="Po kolika dnech čekání na schválení se praxe zobrazí na dashboardu jako zaseknutá (1–365 dní).",
    )
    max_upload_size = models.PositiveIntegerField(
        "Maximální velikost nahrávaného souboru (B)",
        default=10 * MB,
        # Horní mez 20 MB; `client_max_body_size 25M` v .docker/Frontend/nginx.conf nechává rezervu na multipart režii.
        validators=[MinValueValidator(1 * MB), MaxValueValidator(20 * MB)],
        help_text="Bajty; 1 MB až 20 MB (20 MB je limit reverzní proxy nginx).",
    )

    class Meta:
        verbose_name = "Systémová nastavení"
        verbose_name_plural = "Systémová nastavení"

    def __str__(self):
        return "Systémová nastavení"

    def save(self, *args, **kwargs):
        # Validátory musí platit i mimo admin (shell, skripty, fixtures).
        self.full_clean()
        # Cache se publikuje až po commitu (django-solo ji jinak plní hned po zápisu → po rollbacku by zůstala neplatná hodnota).
        self.pk = self.singleton_instance_id
        super(SingletonModel, self).save(*args, **kwargs)
        transaction.on_commit(self.set_to_cache)
