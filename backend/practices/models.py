from django.core.validators import FileExtensionValidator
from django.db import models
from django_enumfield import enum

from api.mixins import CancellationMixin
from api.validators import validate_file_size
from users.models import ApprovalStatus

# Číselník krajů ČR. DB číselníky jsou post-MVP,
# krátkodobě řešeno module-level konstantou v practices.models.
REGION_CHOICES = [
    ("PHA", "Hlavní město Praha"),
    ("STC", "Středočeský kraj"),
    ("JHC", "Jihočeský kraj"),
    ("PLK", "Plzeňský kraj"),
    ("KVK", "Karlovarský kraj"),
    ("ULK", "Ústecký kraj"),
    ("LBK", "Liberecký kraj"),
    ("HKK", "Královéhradecký kraj"),
    ("PAK", "Pardubický kraj"),
    ("OLK", "Olomoucký kraj"),
    ("MSK", "Moravskoslezský kraj"),
    ("JHM", "Jihomoravský kraj"),
    ("ZLK", "Zlínský kraj"),
    ("VYS", "Kraj Vysočina"),
]

# BL-05 / RF-02a — „typ úvazku" (employment type) nabídky praxe.
#
# ZÁVAZNÝ číselník dle rozhodnutí vlastníka/garantů 2026-10-11
# (audit/2026-10-04/lanes/guarantor-values.md §1, C21-A): numerická osa
# „Úvazek 0,5" / „Úvazek 1,0". PLACEHOLDER s prefixem `placeholder_` je
# stažen; uložené kódy se normalizují datovou migrací 0014
# (placeholder_part_time → uvazek_0_5, placeholder_full_time → uvazek_1_0).
# Osa zůstává numerická (stávající UI koeficientová osa); další hodnoty
# (DPP/DPČ/HPP apod.) se NEPřidávají bez nového garantského rozhodnutí.
EMPLOYMENT_TYPE_CHOICES = [
    ("uvazek_0_5", "Úvazek 0,5"),
    ("uvazek_1_0", "Úvazek 1,0"),
]

SEMESTER_CHOICES = [("ZS", "Zimní semestr"), ("LS", "Letní semestr")]

# Legacy (BL-05 placeholder) → autoritativní kódy. Používá datová migrace
# 0014_practice_employment_type_codes a legacy mapping test.
EMPLOYMENT_TYPE_LEGACY_CODE_MAP = {
    "placeholder_part_time": "uvazek_0_5",
    "placeholder_full_time": "uvazek_1_0",
}


class ProgressStatus(enum.Enum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class ApplicationClosureReason(enum.Enum):
    """
    Důvod uzavření sběru přihlášek.

    Triggery: 2 týdny před start_date / naplněna kapacita / manuální uzavření katedrou.
    """

    TIME = 0  # Automaticky X dní před start_date
    CAPACITY = 1  # Naplněn available_positions
    MANUAL = 2  # Katedra/admin uzavřela ručně


class PracticeWorkflowState(enum.Enum):
    """
    Stavový automat nabídky praxe (Practice).

    Implementováno (CONTENT_REJECTED netreminální).

    Přechody:
      PENDING_CONTENT_APPROVAL → CONTENT_APPROVED   (katedra schválí obsah)
      PENDING_CONTENT_APPROVAL → CONTENT_REJECTED   (katedra zamítne obsah)
      CONTENT_REJECTED         → PENDING_CONTENT_APPROVAL  (firma přepracuje, netreminální)
      CONTENT_APPROVED         → OPEN_FOR_APPLICATIONS     (automaticky)
      OPEN_FOR_APPLICATIONS    → CLOSED_FOR_APPLICATIONS   (čas/kapacita/manuál)

    Stará pole progress_status + approval_status zůstávají pro backward compat
    (jsou derivována/mapována v rámci data migrace).
    """

    PENDING_CONTENT_APPROVAL = 0  # Výchozí — čeká na schválení obsahu katedrou
    CONTENT_APPROVED = 1  # Katedra schválila obsah nabídky
    CONTENT_REJECTED = 2  # Obsah zamítnut, vrací se k přepracování (netreminální)
    OPEN_FOR_APPLICATIONS = 3  # Na nástěnce, přijímá přihlášky studentů
    CLOSED_FOR_APPLICATIONS = 4  # Sběr přihlášek uzavřen (čas / kapacita / manuál)


class ExternalEmployerInfo(models.Model):
    """
    Textová reprezentace firmy pro mimosystémové praxe.

    Firma se neregistruje v systému — data se ukládají sem.
    Volitelně lze povýšit na EmployerProfile (pole promoted_to) pokud se firma
    později rozhodne zaregistrovat.

    Samostatná tabulka (DRY, možné re-použití pro víc praxí).
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
    # data firmy jsou v ExternalEmployerInfo (FK external_employer).
    # on_delete změněn CASCADE → SET_NULL.
    employer = models.ForeignKey(
        "users.EmployerProfile",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
    )
    # FK na ExternalEmployerInfo pro mimosystémové praxe.
    # Definováno po vytvoření modelu ExternalEmployerInfo — zatím jako string ref.
    external_employer = models.ForeignKey(
        "practices.ExternalEmployerInfo",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="practices",
        help_text="Textová reprezentace firmy pro mimosystémové praxe (is_external=True).",
    )
    # is_external: příznak mimosystémové praxe
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
    # Nový stavový automat — bude jediným zdrojem pravdy po data migraci
    # a po odstranění starých polí. Zatím nullable pro backward compat.
    workflow_state = enum.EnumField(
        PracticeWorkflowState,
        null=True,
        blank=True,
        db_index=True,
        help_text="Stavový automat nabídky. Po data migraci (1.10) nenullable.",
    )
    # Stará pole — zachována pro backward compat, budou odstraněna po FE migraci
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
    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES, null=True, blank=True, default=None)  # noqa: DJ001
    city = models.CharField(max_length=100, blank=True, default="", help_text="Město, kde se praxe koná")
    mentor_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Jméno mentora praxe",
    )
    contact_email = models.EmailField(
        blank=True,
        default="",
        help_text="Kontaktní e-mail nabídky",
    )
    region = models.CharField(
        max_length=32,
        choices=REGION_CHOICES,
        blank=True,
        default="",
        help_text="Kraj, kde se praxe koná",
    )
    # BL-05 / RF-02a — filtr „typ úvazku" v katalogu nabídek.
    # Závazný číselník dle guarantor-values.md §1 (2026-10-11, C21-A),
    # viz EMPLOYMENT_TYPE_CHOICES; default="" pokrývá řádky bez úvazku.
    employment_type = models.CharField(
        max_length=64,
        choices=EMPLOYMENT_TYPE_CHOICES,
        blank=True,
        default="",
        db_index=True,
        help_text=("Typ úvazku nabídky. Závazný číselník dle rozhodnutí garantů/vlastníka (guarantor-values.md, 2026-10-11)."),
    )
    external_details_file = models.FileField(
        upload_to="external_details/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "docx"]), validate_file_size],
        help_text="Soubor s detaily mimosystémové praxe (povinné při is_external=True)",
    )
    is_active = models.BooleanField(blank=True, null=True, db_index=True)
    image_base64 = models.TextField(blank=True, default="")
    # DEPRECATED: coefficient je nahrazen Subject.min_hours.
    # Už se nepoužívá pro výpočet end_date. Zachováno pro backward compat,
    # null=True, blank=True pro migraci.
    coefficient = models.FloatField(default=1.0, null=True, blank=True)
    # Uzavření sběru přihlášek
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

    @property
    def workflow_status_label(self):
        """Kanonický český label inzerce.

        Vzor: ``student_practices.models.StudentPractice.workflow_status_label``.
        """
        if self.is_cancelled:
            return "Stornováno"
        labels = {
            "PENDING_CONTENT_APPROVAL": "Čeká na schválení obsahu",
            "CONTENT_APPROVED": "Čeká na aktivaci",
            "OPEN_FOR_APPLICATIONS": "Aktivní",
            "CLOSED_FOR_APPLICATIONS": "Uzavřeno",
            "CONTENT_REJECTED": "Zamítnutí obsahu",
        }
        return labels.get(self.workflow_state.name if self.workflow_state else "", "Neznámý")
