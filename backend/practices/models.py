from django.db import models
from django_enumfield import enum

from api.mixins import CancellationMixin
from users.models import ApprovalStatus


class ProgressStatus(enum.Enum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class ApplicationClosureReason(enum.Enum):
    """
    Důvod uzavření sběru přihlášek (task 1.5).

    Ref: THESIS_ARCHITECTURE_PLAN.md sekce 3.2, Ministr 5
    OQ5: 2 týdny před start_date / naplněna kapacita / manuální uzavření katedrou.
    """

    TIME = 0  # Automaticky X dní před start_date
    CAPACITY = 1  # Naplněn available_positions
    MANUAL = 2  # Katedra/admin uzavřela ručně


class PracticeWorkflowState(enum.Enum):
    """
    Stavový automat nabídky praxe (Practice).

    Ref: THESIS_ARCHITECTURE_PLAN.md sekce 3.2
    Implementováno dle doporučení autora (OQ3: CONTENT_REJECTED netreminální).

    Přechody:
      PENDING_CONTENT_APPROVAL → CONTENT_APPROVED   (katedra schválí obsah)
      PENDING_CONTENT_APPROVAL → CONTENT_REJECTED   (katedra zamítne obsah)
      CONTENT_REJECTED         → PENDING_CONTENT_APPROVAL  (firma přepracuje, netreminální)
      CONTENT_APPROVED         → OPEN_FOR_APPLICATIONS     (automaticky)
      OPEN_FOR_APPLICATIONS    → CLOSED_FOR_APPLICATIONS   (čas/kapacita/manuál)

    Stará pole progress_status + approval_status zůstávají pro backward compat
    (jsou derivována/mapována v task 1.10 + 4.8).
    """

    PENDING_CONTENT_APPROVAL = 0  # Výchozí — čeká na schválení obsahu katedrou
    CONTENT_APPROVED = 1  # Katedra schválila obsah nabídky
    CONTENT_REJECTED = 2  # Obsah zamítnut, vrací se k přepracování (netreminální)
    OPEN_FOR_APPLICATIONS = 3  # Na nástěnce, přijímá přihlášky studentů
    CLOSED_FOR_APPLICATIONS = 4  # Sběr přihlášek uzavřen (čas / kapacita / manuál)


class ExternalEmployerInfo(models.Model):
    """
    Textová reprezentace firmy pro mimosystémové praxe (task 1.8).

    Firma se neregistruje v systému — data se ukládají sem.
    Volitelně lze povýšit na EmployerProfile (pole promoted_to) pokud se firma
    později rozhodne zaregistrovat.

    Ref: THESIS_ARCHITECTURE_PLAN.md sekce 2.2.8, OQ8
    Doporučení autora: samostatná tabulka (DRY, možné re-použití pro víc praxí).
    """

    name = models.CharField(max_length=200)
    ico = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    contact_name = models.CharField(max_length=100, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    # Volitelná promočka na registrovaný profil (pozdější rozšíření)
    promoted_to = models.ForeignKey(
        "users.EmployerProfile",
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="promoted_from_external",
        help_text="Pokud se firma zaregistrovala, odkaz na EmployerProfile.",
    )
    created_by = models.ForeignKey(
        "users.User",
        models.PROTECT,
        related_name="created_external_employers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "external_employer_info"

    def __str__(self):
        return f"{self.name} (IČO: {self.ico})" if self.ico else self.name


class Practice(CancellationMixin, models.Model):
    practice_id = models.AutoField(primary_key=True)
    # employer je nullable: pro mimosystémové praxe (is_external=True) bude NULL,
    # data firmy jsou v ExternalEmployerInfo (FK external_employer, task 1.8).
    # on_delete změněn CASCADE → SET_NULL (task 1.5 / N5 fix).
    employer = models.ForeignKey(
        "users.EmployerProfile",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
    )
    # FK na ExternalEmployerInfo pro mimosystémové praxe (task 1.8).
    # Definováno po vytvoření modelu ExternalEmployerInfo — zatím jako string ref.
    external_employer = models.ForeignKey(
        "practices.ExternalEmployerInfo",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
        help_text="Textová reprezentace firmy pro mimosystémové praxe (is_external=True).",
    )
    # is_external: příznak mimosystémové praxe (Zadavatel 1.1, Ministr 6)
    is_external = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True = mimosystémová praxe (firma není registrovaná v systému).",
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
    # Nový stavový automat (task 1.3) — bude jediným zdrojem pravdy po data migraci (1.10)
    # a po odstranění starých polí (task 2.1+). Zatím nullable pro backward compat.
    workflow_state = enum.EnumField(
        PracticeWorkflowState,
        null=True,
        blank=True,
        db_index=True,
        help_text="Stavový automat nabídky. Po data migraci (1.10) nenullable.",
    )
    # Stará pole — zachována pro backward compat, budou odstraněna po FE migraci (task 4.8)
    progress_status = enum.EnumField(ProgressStatus, db_index=True)
    approval_status = enum.EnumField(ApprovalStatus, db_index=True)
    contact_user = models.ForeignKey(
        "users.OrganizationUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
    )
    skills = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(blank=True, null=True, db_index=True)
    image_base64 = models.TextField(blank=True, default="")
    # DEPRECATED (task 1.7 → 3.9): coefficient je nahrazen Subject.min_hours.
    # Už se nepoužívá pro výpočet end_date. Zachováno pro backward compat,
    # null=True, blank=True pro migraci.
    coefficient = models.FloatField(default=1.0, null=True, blank=True)
    # Uzavření sběru přihlášek (task 1.5, Ministr 5)
    closed_for_applications_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp uzavření sběru přihlášek.",
    )
    closed_reason = enum.EnumField(
        ApplicationClosureReason,
        null=True,
        blank=True,
        help_text="Důvod uzavření sběru přihlášek (TIME/CAPACITY/MANUAL).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "practices"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or super().__str__()
