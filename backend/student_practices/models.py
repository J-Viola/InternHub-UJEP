import logging
import random
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import OneToOneRel
from django_enumfield import enum

from api.mixins import CancellationMixin
from api.models import SystemSettings
from practices.models import ProgressStatus
from student_practices.messages import StudentPracticeMessages
from users.models import ApprovalStatus

logger = logging.getLogger(__name__)


class EmployerInvitationStatus(enum.Enum):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2
    CANCELLED = 3
    EXPIRED = 4  # pozvánka expirovala po expiration_date


class StudentPracticeWorkflowState(enum.Enum):
    """
    Stavový automat přihlášky studenta na praxi (StudentPractice).

    Implementace:
      - CONTRACTED spouští katedra ručně (po fyzickém doručení smlouvy)
      - STARTED/ENDED dle data + podmínka CONTRACTED (datum = trigger)

    Přechody:
      APPLIED              → PRELIMINARY_APPROVED  (katedra schválí studenta)
      APPLIED              → REJECTED              (katedra/firma zamítne)
      PRELIMINARY_APPROVED → CONTRACTED            (katedra ručně po podpisu smlouvy)
      PRELIMINARY_APPROVED → REJECTED              (zamítnutí)
      CONTRACTED           → STARTED               (datum start_date + podmínka CONTRACTED)
      STARTED              → ENDED                 (datum end_date / manuál)
      ENDED                → COMPLETED             (katedra udělí zápočet)

    Stará pole approval_status + progress_status zůstávají pro backward compat.
    """

    APPLIED = 0  # Student se přihlásil (nebo byl pozván a akceptoval)
    PRELIMINARY_APPROVED = 1  # Předběžně schváleno katedrou (school_approved=True)
    REJECTED = 2  # Zamítnutí přihlášky — terminální stav
    CONTRACTED = 3  # Zasmluvněno — trojstranná smlouva podepsána
    STARTED = 4  # Student fyzicky nastoupil
    ENDED = 5  # Praxe ukončena (časový rámec uplynul)
    COMPLETED = 6  # Zápočet udělen — terminální úspěšný stav
    AWAITING_CONTRACT = 7  # Čeká na zasmluvnění / doručení smlouvy
    AWAITING_DOCUMENTS = 8  # Čeká na nahrání/kontrolu dokumentů
    DOCUMENTS_REJECTED = 9  # Dokulenty zamítnuty, očekává se re-upload
    AWAITING_CONTENT_APPROVAL = 10  # Čeká na schválení obsahu garnatem u externí praxe
    CONTENT_REJECTED = 11  # Obsah zamítnut garantem, očekává se oprava
    CONTENT_APPROVED = 12  # Obsah externí praxe schválen garantem
    DOCUMENTS_RESUBMITTED = 13  # Opravené dokumenty nahrány, čeká na review (C19-B/T2c — upload ≠ approval)


class EmployerInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(
        "users.EmployerProfile",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    user = models.ForeignKey(
        "users.StudentUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    practice = models.ForeignKey(
        "practices.Practice",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    submission_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    message = models.TextField(blank=True, default="")
    status = enum.EnumField(EmployerInvitationStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employer_invitations"
        # Constraint unique_invitation_per_student_practice odstraněn:
        # Re-aplikace povolena — student smí dostat druhou pozvánku
        # po odmítnuté přihlášce.

    def __str__(self):
        return f"Invitation {self.invitation_id} for {self.user} to {self.practice}"


class DocumentType(enum.Enum):
    CONTRACT = 0
    CONTENT = 1
    FEEDBACK = 2


class DocumentStatus(enum.Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    document = models.FileField(upload_to="documents", blank=True, null=True, db_index=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    document_type = enum.EnumField(DocumentType)
    status = enum.EnumField(DocumentStatus, default=DocumentStatus.PENDING)
    review_note = models.TextField(blank=True, default="")
    late_submission = models.BooleanField(default=False, help_text="True pokud byl dokument nahrán po end_date praxe")

    class Meta:
        db_table = "uploaded_documents"

    def __str__(self):
        return self.document.name or super().__str__()

    @property
    def student_practice(self):
        for rel in self._meta.get_fields():
            # Check by name to avoid reference issues before class definition
            if isinstance(rel, OneToOneRel) and rel.related_model.__name__ == "StudentPractice":
                related_object = getattr(self, rel.get_accessor_name(), None)
                if related_object is not None:
                    return related_object
        return None

    def user_has_permission(self, user):
        """
        Centralized permission check for document access.
        """
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        sp = self.student_practice
        if not sp:
            # If document is not linked to any student practice,
            # we might need additional logic here for other types of documents.
            return False

        # Lazy imports to avoid circular dependencies
        from users.models import (
            DepartmentRole,
            OrganizationUser,
            ProfessorUser,
            StudentUser,
            UserSubjectType,
        )

        # 1. Student access (must be the owner)
        if isinstance(user, StudentUser):
            return sp.user_id == user.user_id

        # 2. Professor / Department Head access
        if isinstance(user, ProfessorUser):
            subject = sp.practice.subject
            # Check if professor is assigned to the subject
            if subject.user_subjects.filter(user=user, role=UserSubjectType.Professor, is_active=True).exists():
                return True
            # Check if professor is head of department
            if user.department_role == DepartmentRole.HEAD and user.department_id == subject.department_id:
                return True
            # Garant praxe své katedry (stejné pravidlo jako u CanCancelPractice)
            if user.is_garant_praxe and user.department_id == subject.department_id:
                return True

        # 3. Organization access
        if isinstance(user, OrganizationUser):
            # Check if user belongs to the employer organization of the practice
            # None == None (externí praxe × organizace bez firmy) nesmí oprávnit
            return user.employer_profile_id is not None and sp.practice.employer_id == user.employer_profile_id

        return False


class DocumentHelper:
    DOCUMENT_FILES = {
        DocumentType.CONTRACT: "default_contract.docx",
        DocumentType.FEEDBACK: "default_feedback.docx",
        DocumentType.CONTENT: "default_content.docx",
    }

    @staticmethod
    def create_default_document(document_type: DocumentType, user_id: int):
        file_name = DocumentHelper.DOCUMENT_FILES.get(document_type)
        if not file_name:
            raise ValueError(f"Unsupported document type: {document_type}")
        file_path = settings.MEDIA_ROOT / "default_documents" / file_name

        if not file_path.exists():
            logger.warning("Default document %s not found.", file_path)
            return None

        try:
            from django.utils import timezone

            with open(file_path, "rb") as f:
                document_file = File(f)
                document_file.name = f"default_{DocumentHelper.create_name_for_document(document_type, user_id, file_name)}"
                document = UploadedDocument(
                    document_type=document_type,
                    document=document_file,
                    uploaded_at=timezone.now(),
                )
                document.save()
                return document
        except Exception as e:
            logger.error("Error creating default document: %s", str(e))
            return None

    @staticmethod
    def create_name_for_document(document_type: DocumentType, user_id: int, file_name: str):
        import os
        import uuid

        from django.utils import timezone

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

        # Sanitize original file name to prevent path traversal
        safe_file_name = os.path.basename(file_name)
        ext = safe_file_name.rsplit(".", 1)[-1].lower() if "." in safe_file_name else "docx"

        unique_suffix = uuid.uuid4().hex[:6]
        return f"{document_type.name.lower()}_{user_id}_{timestamp}_{unique_suffix}.{ext}"

    @staticmethod
    def assign_default_documents(student_practice):
        """
        Explicitly generates and assigns default documents to a StudentPractice instance.
        """
        try:
            user_id = student_practice.user.id
        except (AttributeError, ValueError, models.ObjectDoesNotExist):
            user_id = random.randint(0, 99999999)

        docs_created = 0

        if not student_practice.contract_document:
            doc = DocumentHelper.create_default_document(DocumentType.CONTRACT, user_id)
            if doc:
                student_practice.contract_document = doc
                docs_created += 1

        if not student_practice.content_document:
            doc = DocumentHelper.create_default_document(DocumentType.CONTENT, user_id)
            if doc:
                student_practice.content_document = doc
                docs_created += 1

        if not student_practice.feedback_document:
            doc = DocumentHelper.create_default_document(DocumentType.FEEDBACK, user_id)
            if doc:
                student_practice.feedback_document = doc
                docs_created += 1

        if docs_created == 0:
            logger.error(
                "No default documents could be created for StudentPractice %s. "
                "Templates are missing from %s/default_documents/. "
                "Practice cannot progress without documents.",
                student_practice.pk,
                settings.MEDIA_ROOT,
            )

        student_practice.save()


def validate_contract_document_type(value):
    if value and value.document_type != DocumentType.CONTRACT:
        raise ValidationError(StudentPracticeMessages.CONTRACT_DOC_REQUIRED)


def validate_feedback_document_type(value):
    if value and value.document_type != DocumentType.FEEDBACK:
        raise ValidationError(StudentPracticeMessages.FEEDBACK_DOC_REQUIRED)


def validate_content_document_type(value):
    if value and value.document_type != DocumentType.CONTENT:
        raise ValidationError(StudentPracticeMessages.CONTENT_DOC_REQUIRED)


class PracticeRegistration(models.Model):
    """
    BL-10 (Schema Option A, rozhodnutí Q2-A): registrace předmětu studenta.

    Identita registrace = (student, subject, year); jedna registrace drží
    N samostatných smluvních vztahů (``StudentPractice`` přes ``registration``
    FK, related_name="relationships") — N je neomezené a re-entry po stornu
    je povolen (Q2-A; ``unique_active_student_practice_per_user`` je podmíněný
    ``is_cancelled=False`` a N neomezuje). Historie (ActionLog/Notification
    řetězec přes ``StudentPractice`` PK) zůstává zachována beze změny (I6).
    """

    registration_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        "users.StudentUser",
        on_delete=models.CASCADE,
        related_name="practice_registrations",
    )
    subject = models.ForeignKey(
        "subject.Subject",
        on_delete=models.PROTECT,
        related_name="practice_registrations",
    )
    year = models.IntegerField(help_text="Akademický rok registrace (Q2-A identita).")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "practice_registrations"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "year"],
                name="unique_registration_student_subject_year",
            )
        ]

    def __str__(self):
        return f"Registrace {self.student} / {self.subject} / {self.year}"

    def countable_hours(self) -> int:
        """
        Q1-A (I2): součet schváleně započitatelných hodin registrace.

        Stornované smluvní vztahy se NEPOČÍTAJÍ (jejich hodiny směřují do
        ničeho); jediná agregační cesta pro registraci. Porovnání s
        ``Subject.min_hours`` ponecháno volajícímu (hodnoty KI/KMA
        schvalují garanti — C21).
        """
        from django.db.models import Sum

        total = self.relationships.filter(is_cancelled=False).aggregate(total=Sum("hours_completed"))["total"]
        return total or 0


class StudentPractice(CancellationMixin, models.Model):
    student_practice_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        "users.StudentUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="student_practices",
    )
    practice = models.ForeignKey(
        "practices.Practice",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="student_practices",
    )
    application_date = models.DateField(blank=True, null=True)
    # Nový stavový automat — bude jediným zdrojem pravdy po data migraci.
    # Nullable pro backward compat — naplní jej data migration.
    workflow_state = enum.EnumField(
        StudentPracticeWorkflowState,
        null=True,
        blank=True,
        db_index=True,
        help_text="Stavový automat přihlášky. Po data migraci (1.10) nenullable.",
    )
    cancelled_from_state = enum.EnumField(StudentPracticeWorkflowState, null=True, blank=True)
    # Stará pole — zachována pro backward compat, budou odstraněna po FE migraci
    approval_status = enum.EnumField(ApprovalStatus)
    progress_status = enum.EnumField(ProgressStatus)
    rejection_reason = models.TextField(
        blank=True,
        default="",
        validators=[MinLengthValidator(10)],
        help_text="Důvod zamítnutí přihlášky nebo obsahu praxe (min 10 znaků)",
    )
    contract_received_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Datum doručení / podpisu smlouvy",
    )
    hours_completed = models.IntegerField(blank=True, null=True)
    # cancellation_reason a cancelled_by pocházejí z CancellationMixin.
    # Původní cancelled_by_user (FK na StagUser) odstraněn — nahrazeno mixin polem
    # cancelled_by (FK na User, obecnější). Pole nikdy neplněno.
    cancellation_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="A-12: čas stornování praxe studentem; storno blokuje novou žádost, dokud ho garant nevezme na vědomí",
    )
    year = models.IntegerField(blank=True, null=True)
    # BL-10 (Schema Option A): registrace předmětu (student, subject, year).
    # Nullable během přechodu — backfill datovou migrací (Q4-A); řádky bez
    # možného zařazení (subject/user/year k nedovození) zůstávají NULL a jsou
    # v migraci logovány jako manuální triáž. SET_NULL = historie se neztrácí.
    registration = models.ForeignKey(
        "PracticeRegistration",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="relationships",
        help_text="BL-10: registrace předmětu (student, subject, year); NULL = čeká na backfill nebo manuální triáž (Q4-A).",
    )
    contract_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_contract",
        limit_choices_to={"document_type": DocumentType.CONTRACT},
        validators=[validate_contract_document_type],
        null=True,
    )
    content_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_content",
        limit_choices_to={"document_type": DocumentType.CONTENT},
        validators=[validate_content_document_type],
        null=True,
    )
    feedback_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_feedback",
        limit_choices_to={"document_type": DocumentType.FEEDBACK},
        validators=[validate_feedback_document_type],
        null=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    school_approved = models.BooleanField(default=False)
    employer_approved = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True, help_text="Poslední změna záznamu (včetně přechodů stavu)")
    # Idempotence notifikací — viz api.SystemSettings.
    contract_overdue_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Čas posledního zaslání notifikace o prodlení se zasmluvněním (idempotence)",
    )
    last_urgency_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Čas poslední odeslané urgence před zahájením (idempotence)",
    )
    urgency_level = models.PositiveIntegerField(
        default=0,
        help_text="Úroveň urgence 0-3 dle settings.PRACTICE_URGENCY_DAYS",
    )

    class Meta:
        db_table = "student_practices"
        indexes = [
            models.Index(fields=["user", "is_cancelled"]),
            models.Index(fields=["workflow_state", "is_cancelled"]),
            models.Index(fields=["application_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["practice", "user"],
                condition=models.Q(is_cancelled=False),
                name="unique_active_student_practice_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.practice} (status: {self.approval_status})"

    @property
    def workflow_status(self):
        """Backward-compat property. Returns string derived from workflow_state."""
        if self.is_cancelled:
            return "CANCELLED"
        if self.workflow_state is None:
            return "UNKNOWN"
        return (
            self.workflow_state.name
        )  # e.g., "APPLIED", "PRELIMINARY_APPROVED", "CONTRACTED", "STARTED", "COMPLETED", "REJECTED", "CANCELLED"

    @property
    def workflow_status_label(self):
        """Human-readable Czech label for workflow_state - canonical."""
        if self.is_cancelled:
            return "Stornováno"
        labels = {
            "APPLIED": "Čeká na schválení garanta",
            "PRELIMINARY_APPROVED": "Čeká na schválení organizací",
            "REJECTED": "Přihláška na praxi odmítnuta",
            "CONTRACTED": "Zasmluvněno",
            "STARTED": "Zahájeno",
            "ENDED": "Ukončeno",
            "COMPLETED": "Splněno",
            "AWAITING_CONTRACT": "Čeká na zasmluvnění",
            "AWAITING_DOCUMENTS": "Čeká na schválení dokumentů",
            "DOCUMENTS_REJECTED": "Dokumenty zamítnuty",
            "DOCUMENTS_RESUBMITTED": "Opravené dokumenty čekají na kontrolu",
            "AWAITING_CONTENT_APPROVAL": "Čeká na schválení obsahu",
            "CONTENT_APPROVED": "Obsah praxe schválen",
            "CONTENT_REJECTED": "Zamítnutí obsahu",
        }
        return labels.get(self.workflow_state.name if self.workflow_state is not None else "", "Neznámý")

    # ------------------------------------------------------------------
    # (SMLOUVA_PO_TERMINU): computed flag prodlení se zasmluvněním
    # ------------------------------------------------------------------

    @property
    def contract_overdue(self) -> bool:
        """
        Praxe ve stavu AWAITING_CONTRACT déle než ``SystemSettings.practice_contract_overdue_days``.

        Stáří ve stavu se počítá z ActionLog přechodu (STATE_TRANSITION do
        AWAITING_CONTRACT); pokud přechodový záznam není k dispozici (data
        mimo state machine), používá se fallback ``updated_at``.
        """
        from django.utils import timezone

        if self.workflow_state != StudentPracticeWorkflowState.AWAITING_CONTRACT:
            return False

        overdue_days = SystemSettings.get_solo().practice_contract_overdue_days
        entered_at = self._awaiting_contract_since()
        if entered_at is None:
            return False
        return timezone.now() - entered_at > timedelta(days=overdue_days)

    def _awaiting_contract_since(self):
        """
        Čas vstupu do AWAITING_CONTRACT dle ActionLog STATE_TRANSITION
        (fallback: updated_at, pokud log chybí).
        """
        from users.constants import ActionLogType
        from users.models import ActionLog

        try:
            log = (
                ActionLog.objects.filter(
                    object_type="StudentPractice",
                    object_id=self.student_practice_id,
                    action_type=ActionLogType.STATE_TRANSITION,
                    action_description__contains="-> AWAITING_CONTRACT",
                )
                .order_by("-action_date")
                .first()
            )
        except Exception:
            log = None

        if log is not None and log.action_date is not None:
            return log.action_date
        return self.updated_at


class Evaluation(models.Model):
    evaluation_id = models.AutoField(primary_key=True)
    student_practice = models.OneToOneField(
        StudentPractice,
        on_delete=models.CASCADE,
        related_name="evaluation",
    )
    expertise_rating = models.IntegerField(default=5, help_text="Odbornost (1-5)")
    expertise_comment = models.TextField(blank=True, default="")

    communication_rating = models.IntegerField(default=5, help_text="Komunikace (1-5)")
    communication_comment = models.TextField(blank=True, default="")

    initiative_rating = models.IntegerField(default=5, help_text="Iniciativa (1-5)")
    initiative_comment = models.TextField(blank=True, default="")

    overall_comment = models.TextField(blank=True, default="")
    hours_completed = models.PositiveIntegerField(null=True, blank=True, help_text="Potvrzený počet hodin praxe")
    pdf_file = models.FileField(upload_to="evaluations/pdf/", blank=True, null=True)
    pdf_protokol = models.FileField(upload_to="evaluations/protokol/", blank=True, null=True)

    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations_given",
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluations"

    def __str__(self):
        return f"Evaluation for SP #{self.student_practice_id}"
