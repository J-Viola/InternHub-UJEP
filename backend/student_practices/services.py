import io
import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone
from notifications.models import NotificationType
from notifications.services import EmailService, NotificationService
from rest_framework.exceptions import PermissionDenied
from templates.documents.content_generator import ContentGenerator
from templates.documents.contract_generator import ContractGenerator
from templates.documents.feedback_generator import FeedbackGenerator
from templates.documents.report_generator import ReportGenerator

from api.helpers import can_manage_practice
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.messages import StudentPracticeMessages
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    DocumentType,
    EmployerInvitation,
    EmployerInvitationStatus,
    PracticeRegistration,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus, OrganizationUser, ProfessorUser, StagRoleEnum, StudentUser
from users.services import fetch_student_data_from_stag

logger = logging.getLogger(__name__)

SP_TRANSITIONS = {
    StudentPracticeWorkflowState.APPLIED: [
        StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.PRELIMINARY_APPROVED: [
        StudentPracticeWorkflowState.AWAITING_CONTRACT,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.AWAITING_CONTRACT: [
        StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
        StudentPracticeWorkflowState.CONTRACTED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.AWAITING_DOCUMENTS: [
        StudentPracticeWorkflowState.CONTRACTED,
        StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
    ],
    StudentPracticeWorkflowState.DOCUMENTS_REJECTED: [
        StudentPracticeWorkflowState.REJECTED,  # T2c: výhradně admin + důvod (guard níže)
        # C19-B/T2c: přímé hrany AWAITING_DOCUMENTS/ENDED odstraněny —
        # oprava vede POUZE přes upload → DOCUMENTS_RESUBMITTED → review.
    ],
    StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED: [
        StudentPracticeWorkflowState.AWAITING_DOCUMENTS,  # T2c: review schválilo (střední cyklus)
        StudentPracticeWorkflowState.ENDED,  # T2c: review schválilo (konečné doklady)
        StudentPracticeWorkflowState.DOCUMENTS_REJECTED,  # T2c: review zamítlo — smyčka
        StudentPracticeWorkflowState.REJECTED,  # T2c: výhradně admin + důvod (guard níže)
    ],
    StudentPracticeWorkflowState.CONTRACTED: [
        StudentPracticeWorkflowState.STARTED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.STARTED: [
        StudentPracticeWorkflowState.ENDED,
    ],
    StudentPracticeWorkflowState.ENDED: [
        StudentPracticeWorkflowState.COMPLETED,
        StudentPracticeWorkflowState.REJECTED,
        StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
    ],
    StudentPracticeWorkflowState.COMPLETED: [],
    StudentPracticeWorkflowState.REJECTED: [],
}

# MANUAL_SP_TRANSITIONS: transitions for external (manual) practices.
# Derived from SP_TRANSITIONS to avoid duplication — the shared states
# (AWAITING_CONTRACT, AWAITING_DOCUMENTS, DOCUMENTS_REJECTED, CONTRACTED,
#  STARTED, ENDED, COMPLETED, REJECTED) are identical.
# Only APPLIED/PRELIMINARY_APPROVED and the CONTENT_* chain differ.
_MANUAL_BASE = {
    StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL: [
        StudentPracticeWorkflowState.CONTENT_APPROVED,
        StudentPracticeWorkflowState.CONTENT_REJECTED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.CONTENT_REJECTED: [
        StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.CONTENT_APPROVED: [
        StudentPracticeWorkflowState.AWAITING_CONTRACT,
        StudentPracticeWorkflowState.CONTRACTED,
        StudentPracticeWorkflowState.REJECTED,
    ],
}

MANUAL_SP_TRANSITIONS = {**_MANUAL_BASE}
# Copy shared states from SP_TRANSITIONS (skip APPLIED and PRELIMINARY_APPROVED
# which have different flow in manual mode).
for _state, _transitions in SP_TRANSITIONS.items():
    if _state in (
        StudentPracticeWorkflowState.AWAITING_CONTRACT,
        StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
        StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
        StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED,
        StudentPracticeWorkflowState.CONTRACTED,
        StudentPracticeWorkflowState.STARTED,
        StudentPracticeWorkflowState.ENDED,
        StudentPracticeWorkflowState.COMPLETED,
        StudentPracticeWorkflowState.REJECTED,
    ):
        MANUAL_SP_TRANSITIONS[_state] = _transitions


def get_transitions_matrix(sp: StudentPractice) -> dict:
    if sp.practice and getattr(sp.practice, "is_external", False):
        return MANUAL_SP_TRANSITIONS
    return SP_TRANSITIONS


def _check_contract_capacity(practice: Practice) -> None:
    """
    Kapacitní kontrola při alokaci.

    Přechod do CONTRACTED je povolen pouze pokud ``approved_count`` (počet
    již alokovaných studentů — CONTRACTED/STARTED/ENDED/COMPLETED) je menší
    než ``practice.available_positions``. Plno → ValueError("CAPACITY_FULL").

    Pozor: pole kapacity je ``available_positions`` (NE ``capacity``).
    """
    if practice is None or practice.available_positions is None:
        return
    # T2a: počítají se jen celková umístění (CONTRACTED/STARTED/ENDED/COMPLETED);
    # stornované ani axis-pending přihlášky se NEPOČÍTAJÍ.
    approved_count = StudentPractice.objects.filter(
        practice=practice,
        is_cancelled=False,
        workflow_state__in=[
            StudentPracticeWorkflowState.CONTRACTED,
            StudentPracticeWorkflowState.STARTED,
            StudentPracticeWorkflowState.ENDED,
            StudentPracticeWorkflowState.COMPLETED,
        ],
    ).count()
    if approved_count >= practice.available_positions:
        raise ValueError("CAPACITY_FULL")


class AxesIncompleteError(ValueError):
    """T1/C06-A: pokus o přechod do CONTRACTED bez obou schvalovacích os.

    Volání služby (přímé i HTTP) transakčně selže dřív, než cokoli uloží;
    HTTP vrstva překládá na ``{"error_code": "AXES_INCOMPLETE"}`` (view).
    """


def record_own_approval_axis(sp, actor) -> bool:
    """
    T1/C06-A — centrální zápis VLASTNÍ approval osy aktéra.

    - OrganizationUser → ``employer_approved`` (osa zaměstnavatele),
    - StudentUser → žádná osa (T1: receipt-only),
    - škola (ProfessorUser, garant/pedagog; admin = superuser/staff) →
      ``school_approved``,
    - NEZNÁMÁ role → žádná osa (helper NENÍ autorizační kontrola — kdo
      smí přechod, řeší role/scope check; zde se jen nezapisuje cizí osa).

    Nikdy nezapíše cizí osu. Vrací True, pokud jsou po zápisu obě nezávislé
    osy schváleny. Neminí workflow_state ani approval_status — postup do
    CONTRACTED řídí brána v ``transition_student_practice_state`` (služba),
    confirm view a document-review, viz finding 1.
    """
    if isinstance(actor, OrganizationUser):
        sp.employer_approved = True
    elif isinstance(actor, StudentUser):
        pass  # receipt-only (T1)
    elif isinstance(actor, ProfessorUser) or getattr(actor, "is_superuser", False) or getattr(actor, "is_staff", False):
        sp.school_approved = True
    # jinak (neznámá role): žádná osa — helper se nespoléhá jako autorizace
    return bool(sp.school_approved) and bool(sp.employer_approved)


def ensure_practice_registration(student, subject_id, year) -> "PracticeRegistration | None":
    """
    BL-10/Q2-A: get_or_create registrace předmětu (student, subject, year).

    N smluvních vztahů na registraci je neomezených; re-entry po stornu je
    povolen (Q2-A). Vrací None, pokud student nebo subject chybí — řádek SP
    pak zůstává ``registration=NULL`` (Q4-A: manuální triáž, migrace loguje).
    """
    if student is None or subject_id is None:
        return None
    registration, _created = PracticeRegistration.objects.get_or_create(
        student_id=student.pk,
        subject_id=subject_id,
        year=year,
    )
    return registration


def student_has_blocking_cancellation(user, practice) -> bool:
    """
    C03-A + BL-10: blok nové žádosti, dokud pro stejnou REGISTRACI
    (student, subject, year — identita dle Q2-A) neexistuje nevyřízené
    storno (legacy okamžité) ANEBO nevyřízená žádost o storno (C02-A).

    Plná identita: pendingřádek napojený na registraci stejného
    (student, subject, year) blokuje; registrace jiného roku je jiná
    registrace → neblokuje. Legacy fallback: řádky BEZ registration FK
    (před-backfillem / triáž) blokují předmětově (rok-agnosticky) — fail-closed.

    JEDNO volání .filter() (žádný řetězený .filter) — bílé krabice testy
    (practices/tests/test_services.py) mockují přesnou sekvenci volání.
    """
    from django.db.models import Q

    return StudentPractice.objects.filter(
        Q(user=user)
        & Q(cancellation_resolved_at__isnull=True)
        & (
            Q(registration__isnull=False, registration__subject_id=practice.subject_id, registration__year=date.today().year)
            | Q(registration__isnull=True, practice__subject_id=practice.subject_id)
        )
        & (Q(is_cancelled=True) | Q(cancellation_requested_at__isnull=False))
    ).exists()


def _generate_completion_protocol(sp: StudentPractice) -> None:
    """
    vygeneruje „Protokol o absolvování odborné praxe" (PDF) a uloží
    ho do ``Evaluation.pdf_protokol``, pokud evaluace existuje a protokol je prázdný.

    Download probíhá přes existující mechanismus (``EvaluationSerializer.pdf_protokol``
    URL → servírování z MEDIA_ROOT/storage; dedikovaný endpoint může doplnit později).
    Selhání generování NIKDY nezablokuje samotný přechod do COMPLETED.
    """
    from django.core.files.base import ContentFile

    from student_practices.pdf_service import PDFCompletionProtocolGenerator

    try:
        pdf_bytes = PDFCompletionProtocolGenerator.generate_pdf(sp)
    except Exception:
        logger.exception("Failed to generate completion protocol PDF for SP %s", getattr(sp, "student_practice_id", None))
        return

    evaluation = getattr(sp, "evaluation", None)
    if evaluation is None or evaluation.pdf_protokol:
        # Bez evaluace nebo s již uloženým mentorským protokolem neukládáme (žádný přepis).
        return

    try:
        filename = f"protokol_absolvovani_sp_{sp.student_practice_id}.pdf"
        evaluation.pdf_protokol.save(filename, ContentFile(pdf_bytes), save=True)
    except Exception:
        logger.exception("Failed to store completion protocol PDF for SP %s", sp.student_practice_id)


@transaction.atomic
def withdraw_student_practice(sp, actor):
    """
    Student withdraws their application.
    Only allowed in APPLIED or PRELIMINARY_APPROVED state.
    Sets workflow_state to REJECTED.
    """
    sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)

    if sp.is_cancelled:
        raise ValueError(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY)

    allowed_states = (
        StudentPracticeWorkflowState.APPLIED,
        StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
    )
    if sp.workflow_state not in allowed_states:
        raise ValueError("Žádost lze stáhnout pouze ve stavu APPLIED nebo PRELIMINARY_APPROVED.")

    old_state = sp.workflow_state
    sp.workflow_state = StudentPracticeWorkflowState.REJECTED
    sp.approval_status = ApprovalStatus.REJECTED
    sp.save()

    # ActionLog
    ActionLogService.log(
        user=actor,
        action_type=ActionLogType.STORNO,
        object_type="StudentPractice",
        object_id=sp.student_practice_id,
        description=(f"Student stahl zadost ID {sp.student_practice_id}: " f"{old_state.name if old_state else 'None'} -> REJECTED"),
    )

    # Notify garant (subject manager)
    practice = sp.practice
    if practice and practice.subject and practice.subject.subject_manager:
        garant = practice.subject.subject_manager
        NotificationService.create_notification(
            recipient=garant,
            verb="APPLICATION_WITHDRAWN",
            message=f"Student {sp.user.full_name} stáhl svou žádost na praxi '{practice.title}'.",
            actor=actor,
            target=sp,
            notification_type=NotificationType.WARNING,
        )

    # Notify organization contact
    org_contact = getattr(practice, "contact_user", None) if practice else None
    if org_contact:
        NotificationService.create_notification(
            recipient=org_contact,
            verb="APPLICATION_WITHDRAWN",
            message=f"Student {sp.user.full_name} stáhl svou žádost na praxi '{practice.title}'.",
            actor=actor,
            target=sp,
            notification_type=NotificationType.WARNING,
        )

    return sp


def _check_transition_role(actor, from_state, to_state, sp) -> None:
    """
    Validates that the actor has the right role to perform the given transition.

    Rules:
    - StudentUser:     only DOCUMENTS_REJECTED→AWAITING_DOCUMENTS, CONTENT_REJECTED→AWAITING_CONTENT_APPROVAL
                       — a POUZE na vlastní přihlášce (ownership guard, BE-015)
    - OrganizationUser (employer): only from PRELIMINARY_APPROVED → AWAITING_CONTRACT / CONTRACTED / REJECTED
    - Garant/Professor (VY/VK role): all remaining transitions
    - Admin/superuser: any transition

    Raises ValueError if the actor is not authorized.
    Raises PermissionDenied if a student attempts a repair transition on a
    foreign (non-owned) StudentPractice — authorization, not workflow error.
    """
    # Admin / superuser — always allowed
    if getattr(actor, "is_superuser", False):
        return

    if isinstance(actor, StudentUser):
        allowed = [
            # C19-B/T2c: přímé opravné hrany DOCUMENTS_REJECTED → AWAITING_DOCUMENTS/ENDED
            # ODSTRANĚNY — oprava dokumentů vede výhradně přes upload
            # (DOCUMENTS_RESUBMITTED) a review rozhoduje o dalším stavu.
            (StudentPracticeWorkflowState.CONTENT_REJECTED, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL),
        ]
        if (from_state, to_state) not in allowed:
            raise ValueError("Student nemůže provést tento přechod.")
        # Ownership guard (BE-015): opravné přechody jen na vlastní přihlášce.
        # Cizí student je odmítnut dřív, než dojde k jakékoli mutaci.
        if sp.user_id != actor.pk:
            raise PermissionDenied("Přechod je povolen pouze na vlastní přihlášce.")
        return

    if isinstance(actor, OrganizationUser) and hasattr(actor, "employer_profile"):
        # Organization can only transition from PRELIMINARY_APPROVED
        if from_state != StudentPracticeWorkflowState.PRELIMINARY_APPROVED:
            raise ValueError("Organizace nemůže provést tento přechod.")
        allowed_to = [
            StudentPracticeWorkflowState.AWAITING_CONTRACT,
            StudentPracticeWorkflowState.CONTRACTED,
            StudentPracticeWorkflowState.REJECTED,
        ]
        if to_state not in allowed_to:
            raise ValueError("Organizace nemůže provést tento přechod.")
        return

    # Garant / Professor with VY or VK role — all remaining transitions
    if isinstance(actor, ProfessorUser):
        stag_role = getattr(actor, "stag_role", None)
        if stag_role and stag_role.role.lower() in (StagRoleEnum.VY, StagRoleEnum.VK):
            return
        if getattr(actor, "is_garant_praxe", False):
            return

    # Any other authenticated user (incl. staff without VY/VK) — deny
    raise ValueError("Neoprávněná role pro tento přechod.")


class StudentPracticeService:
    @staticmethod
    def get_transitions_matrix(sp=None):
        return get_transitions_matrix(sp)

    @staticmethod
    @transaction.atomic
    def create_invitations(user, practice_id: int, student_ids: list[int]) -> dict:
        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            raise ValueError(StudentPracticeMessages.PRACTICE_NOT_FOUND)

        # Optional: Check if user owns the practice if user is passed
        if hasattr(user, "employer_profile") and practice.employer != user.employer_profile:
            raise ValueError(StudentPracticeMessages.UNAUTHORIZED)

        created_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = StudentUser.objects.get(pk=student_id)

                # Skip if student already has an active practice for this offer
                if (
                    StudentPractice.objects.filter(
                        practice=practice,
                        user=student,
                        is_cancelled=False,
                    )
                    .exclude(workflow_state=StudentPracticeWorkflowState.REJECTED)
                    .exists()
                ):
                    continue

                # Use get_or_create to avoid race condition on duplicate invitations
                invitation, created = EmployerInvitation.objects.get_or_create(
                    practice=practice,
                    user=student,
                    defaults={
                        "employer": practice.employer,
                        "status": EmployerInvitationStatus.PENDING,
                        "submission_date": date.today(),
                    },
                )
                if created:
                    EmailService.notify_student_invitation(invitation)
                    NotificationService.create_notification(
                        recipient=student,
                        verb="INVITATION_RECEIVED",
                        message=f"Dostali jste pozvánku na praxi '{practice.title}' " f"od organizace {practice.employer.company_name}.",
                        actor=user,
                        target=invitation,
                        notification_type=NotificationType.INFO,
                    )
                    created_count += 1
            except StudentUser.DoesNotExist:
                errors.append(f"Student ID {student_id} neexistuje.")

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.INVITATION_CREATE,
            object_type="EmployerInvitation",
            description=f"Vytvořeno {created_count} pozvánek pro praxi ID {practice_id}",
        )

        return {"created": created_count, "errors": errors}

    @staticmethod
    @transaction.atomic
    def transition_student_practice_state(sp, target_state, actor, reason=None):
        """
        Transition a StudentPractice through the workflow state machine.

        Validates the transition against SP_TRANSITIONS, applies side effects
        (approval flags, approval/progress statuses), and logs the action.
        """
        # Refetch with row lock to prevent race conditions
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)

        if sp.is_cancelled:
            raise ValueError(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY)

        # Role-based authorization check (K1)
        if sp.workflow_state is not None:
            _check_transition_role(actor, sp.workflow_state, target_state, sp)

        # Only allow initialization from None to APPLIED
        if sp.workflow_state is None:
            if target_state != StudentPracticeWorkflowState.APPLIED:
                raise ValueError(f"Neinicializovana prihlaska — povolen je pouze prechod do APPLIED, " f"ne do {target_state.name}")
            # Finding 4: inicializace existujícího (null-state) záznamu
            # vyžaduje scope (vlastník/rozsah) — cizí aktér → PermissionDenied
            # (403) s nulovou mutací, dřív cokoli zapíšeme.
            from student_practices.utils import user_can_access_student_practice

            if not user_can_access_student_practice(actor, sp):
                raise PermissionDenied("Inicializace cizí přihlášky není povolena.")
            # action role: studenti (opravné páry) ani organizace null→APPLIED
            # nesmí; škola/admin smí (vlastní scope ověřen výše).
            _check_transition_role(actor, None, target_state, sp)

        allowed = get_transitions_matrix(sp).get(sp.workflow_state)
        if sp.workflow_state is not None and allowed is None:
            raise ValueError(StudentPracticeMessages.TRANSITION_NOT_DEFINED.format(sp.workflow_state))

        if sp.is_cancelled:
            raise ValueError(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY)

        if sp.workflow_state is not None and target_state not in allowed:
            raise ValueError(StudentPracticeMessages.TRANSITION_NOT_ALLOWED.format(sp.workflow_state, target_state))

        # --- T2c: terminální REJECTED z opravného cyklu = výhradně admin + důvod ---
        if (
            sp.workflow_state
            in (
                StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
                StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED,
            )
            and target_state == StudentPracticeWorkflowState.REJECTED
        ):
            if not (getattr(actor, "is_superuser", False) or getattr(actor, "is_staff", False)):
                raise PermissionDenied("Terminální zamítnutí opravného cyklu je vyhrazeno administrátorovi.")
            if not (reason or "").strip():
                raise ValueError("Pro terminální zamítnutí je povinný důvod.")

        # --- BE-004 / BL-004 / BL-10 Q3: dokončení jen se schválenými hodnotícími podklady ---
        if sp.workflow_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.COMPLETED:
            evaluation = getattr(sp, "evaluation", None)  # OneToOne; chybí → None
            if evaluation is None:
                raise ValueError("Dokončení vyžaduje hodnotící podklady: evaluace nebyla vytvořena.")
            feedback_doc = sp.feedback_document
            if feedback_doc is None or feedback_doc.status != DocumentStatus.APPROVED:
                raise ValueError("Dokončení vyžaduje schválené hodnotící podklady: dokument FEEDBACK není schválen.")
            # BL-10/Q3-A (I5): dokončení vyžaduje evaluace VŠECH vztahů
            # registrace; stornované vztahy se nepočítají (Q1-A). Řádky bez
            # registration FK (legacy/triáž) mají jen per-SP gate výše.
            # MAJOR-1 gate round: JEDNO SQL přes reverse-OneToOne isnull —
            # žádný N+1 fetch per vztah (Q2-A povoluje neomezené N).
            if sp.registration_id is not None:
                missing = list(
                    sp.registration.relationships.filter(
                        is_cancelled=False,
                        evaluation__isnull=True,
                    ).values_list("pk", flat=True)
                )
                if missing:
                    raise ValueError(
                        "Dokončení vyžaduje schválené hodnotící podklady VŠECH vztahů registrace "
                        f"(BL-10/Q3-A) — chybí evaluace vztahů: {missing}."
                    )

        # --- C19-B/T2c (finding 5): z DOCUMENTS_RESUBMITTED smí review
        # posunout JEN se schváleným review dokumentu — žádné předčasné
        # ENDED/AWAITING_DOCUMENTS bez schválení opraveného dokumentu. ---
        if sp.workflow_state == StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED and target_state in (
            StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
            StudentPracticeWorkflowState.ENDED,
        ):
            linked_docs = [doc for doc in (sp.contract_document, sp.content_document, sp.feedback_document) if doc is not None]
            if not linked_docs:
                raise ValueError("Opravný přechod vyžaduje dokumenty k review — žádný dokument není připojen.")
            if any(doc.status == DocumentStatus.REJECTED for doc in linked_docs):
                raise ValueError("Opravný přechod blokuje zamítnutý dokument — nejprve proveďte review dokumentů.")
            # Finding 5 (round 3): PŘÍSNÁ varianta — postup vyžaduje, aby byl
            # SCHVÁLEN každý připojený dokument (historický APPROVED stav
            # opraveného dokladu se při re-uploadu resetuje na PENDING, takže
            # staré schválení nemůže uspokojit precondition za opravu).
            # Upload ≠ approval (C19-B); zbytkové PENDING doklady musí review
            # explicitně schválit dřív, než smyčka popojede dál.
            not_approved = [doc for doc in linked_docs if doc.status != DocumentStatus.APPROVED]
            if not_approved:
                pending_types = ", ".join(sorted({DocumentType(doc.document_type).name for doc in not_approved}))
                raise ValueError(
                    "Opravný přechod vyžaduje schválené review VŠECH připojených dokumentů " f"— neschválené: {pending_types}."
                )

        # --- Side effects per transition ---
        if sp.workflow_state == StudentPracticeWorkflowState.APPLIED and target_state == StudentPracticeWorkflowState.PRELIMINARY_APPROVED:
            sp.school_approved = True
            ActionLogService.log(
                user=actor,
                action_type=ActionLogType.APPROVE,
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
                description=(
                    f"Katedra schvalila prihlasku ID {sp.student_practice_id} "
                    f"(prechod {StudentPracticeWorkflowState.APPLIED.name} -> "
                    f"{StudentPracticeWorkflowState.PRELIMINARY_APPROVED.name})"
                ),
            )

        elif (
            sp.workflow_state in (StudentPracticeWorkflowState.APPLIED, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
            and target_state == StudentPracticeWorkflowState.REJECTED
        ):
            sp.approval_status = ApprovalStatus.REJECTED
            ActionLogService.log(
                user=actor,
                action_type=ActionLogType.REJECT,
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
                description=(
                    f"Prihlaska ID {sp.student_practice_id} zamitnuta "
                    f"(prechod {sp.workflow_state.name} -> "
                    f"{StudentPracticeWorkflowState.REJECTED.name})"
                ),
            )

        elif (
            sp.workflow_state == StudentPracticeWorkflowState.PRELIMINARY_APPROVED
            and target_state == StudentPracticeWorkflowState.CONTRACTED
        ):
            # For external practices, employer info must exist before CONTRACTED state
            practice = sp.practice
            if practice.is_external and practice.external_employer is None:
                raise ValueError(StudentPracticeMessages.EXTERNAL_PRACTICE_REQUIRES_EMPLOYER)

            # T1/C06-A: žádné forcování obou os — viz jediná brána níže.
            sp.approval_status = ApprovalStatus.APPROVED

        elif (
            sp.workflow_state == StudentPracticeWorkflowState.AWAITING_CONTRACT and target_state == StudentPracticeWorkflowState.CONTRACTED
        ):
            # kapacitní kontrola při alokaci — plná kapacita blokuje
            # přechod do CONTRACTED. select_for_update na praxi proti race condition.
            practice = sp.practice
            if practice is not None:
                practice = Practice.objects.select_for_update().get(pk=practice.pk)
                sp.practice = practice
                _check_contract_capacity(practice)
            # T1/C06-A: žádné forcování obou os — viz jediná brána níže.
            sp.approval_status = ApprovalStatus.APPROVED

        elif sp.workflow_state == StudentPracticeWorkflowState.CONTRACTED and target_state == StudentPracticeWorkflowState.STARTED:
            sp.progress_status = ProgressStatus.IN_PROGRESS

        elif sp.workflow_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.COMPLETED:
            sp.progress_status = ProgressStatus.COMPLETED

        elif sp.workflow_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.REJECTED:
            sp.approval_status = ApprovalStatus.REJECTED
            ActionLogService.log(
                user=actor,
                action_type=ActionLogType.REJECT,
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
                description=(
                    f"Praxe ID {sp.student_practice_id} nebyla úspěšně dokončena "
                    f"(prechod {StudentPracticeWorkflowState.ENDED.name} -> "
                    f"{StudentPracticeWorkflowState.REJECTED.name})"
                ),
            )

        # ---: Document guard for external practice content approval ---
        if (
            sp.workflow_state == StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL
            and target_state == StudentPracticeWorkflowState.CONTENT_APPROVED
        ):
            if not sp.content_document or not sp.content_document.document:
                raise ValueError("Pro schválení obsahu je nutné nejprve nahrát dokument.")

        # --- T1/C06-A (finding 1, round 3): JEDINÁ osa-zápis + postupová
        # brána pro KAŽDOU generic cestu do CONTRACTED — zápis jen VLASTNÍ
        # osy aktéra (nikdy cizí) a POSTUP JEN PŘI OBOU OSÁCH. Chybí-li
        # druhá osa → AxesIncompleteError transakčně, dřív jakéhokoli
        # save/ActionLog/notifikace (HTTP view překládá na AXES_INCOMPLETE).
        # Kapacita pod stejným lockem níže. ---
        if target_state == StudentPracticeWorkflowState.CONTRACTED and sp.workflow_state != StudentPracticeWorkflowState.CONTRACTED:
            both_axes = record_own_approval_axis(sp, actor)
            if not both_axes:
                missing = [label for label, holds in (("school", sp.school_approved), ("employer", sp.employer_approved)) if not holds]
                raise AxesIncompleteError(
                    "AXES_INCOMPLETE: Přechod do CONTRACTED vyžaduje obě nezávislé "
                    f"schvalovací osy (T1/C06-A) — chybí osa: {', '.join(missing)}."
                )

        # --- T2a/BE-005: jediná kapacitní brána pro KAŽDOU generic cestu
        # do CONTRACTED (AWAITING_DOCUMENTS, CONTENT_APPROVED, externí větve…);
        # AWAITING_CONTRACT větev výše kontroluje stejně (select_for_update). ---
        if target_state == StudentPracticeWorkflowState.CONTRACTED and sp.workflow_state != StudentPracticeWorkflowState.CONTRACTED:
            if sp.practice_id:
                locked_practice = Practice.objects.select_for_update().get(pk=sp.practice_id)
                _check_contract_capacity(locked_practice)

        # --- Apply new workflow state ---
        old_state = sp.workflow_state
        sp.workflow_state = target_state
        sp.save()

        # ---: při přechodu do COMPLETED vygeneruj
        # „Protokol o absolvování odborné praxe" (PDF) ---
        if old_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.COMPLETED:
            _generate_completion_protocol(sp)

        # --- Log state transition ---
        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Zmena stavu prihlasky ID {sp.student_practice_id}: "
                f"{old_state.name if old_state else 'None'} -> {target_state.name} "
                f"({reason or 'bez duvodu'})"
            ),
        )

        # --- Send in-app notification ---
        student = sp.user
        practice_title = sp.practice.title if sp.practice else "N/A"

        # Transition-specific notifications (check both old_state and target_state)
        if (
            old_state == StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL
            and target_state == StudentPracticeWorkflowState.CONTENT_APPROVED
        ):
            EmailService.notify_student_content_approved(sp)
            NotificationService.create_notification(
                recipient=student,
                verb="CONTENT_APPROVED",
                message=f"Obsah praxe '{practice_title}' byl schválen garantem.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif (
            old_state == StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL
            and target_state == StudentPracticeWorkflowState.CONTENT_REJECTED
        ):
            EmailService.notify_student_content_rejected(sp, reason or "")
            NotificationService.create_notification(
                recipient=student,
                verb="CONTENT_REJECTED",
                message=f"Obsah praxe '{practice_title}' byl zamítnut." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif (
            old_state == StudentPracticeWorkflowState.CONTENT_REJECTED
            and target_state == StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL
        ):
            # Notify professor/garant that content was re-submitted for approval
            EmailService.notify_professor_content_approval(sp)
            garant = sp.practice.subject.subject_manager if sp.practice and sp.practice.subject else None
            if garant:
                NotificationService.create_notification(
                    recipient=garant,
                    verb="CONTENT_RESUBMITTED",
                    message=f"Student {student.full_name} znovu odeslal obsah praxe '{practice_title}' ke schválení.",
                    actor=actor,
                    target=sp,
                    notification_type=NotificationType.INFO,
                )
        elif (
            old_state in (StudentPracticeWorkflowState.APPLIED, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
            and target_state == StudentPracticeWorkflowState.AWAITING_CONTRACT
        ):
            EmailService.notify_student_awaiting_contract(sp)
            NotificationService.create_notification(
                recipient=student,
                verb="AWAITING_CONTRACT",
                message=f"Byla zahájena příprava smlouvy k praxi '{practice_title}'.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.INFO,
            )
        elif (
            old_state == StudentPracticeWorkflowState.AWAITING_CONTRACT and target_state == StudentPracticeWorkflowState.AWAITING_DOCUMENTS
        ):
            EmailService.notify_student_awaiting_documents(sp)
            NotificationService.create_notification(
                recipient=student,
                verb="AWAITING_DOCUMENTS",
                message=f"Žádáme o nahrání dokumentů k praxi '{practice_title}'.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.INFO,
            )
        elif (
            old_state == StudentPracticeWorkflowState.AWAITING_DOCUMENTS and target_state == StudentPracticeWorkflowState.DOCUMENTS_REJECTED
        ):
            EmailService.notify_student_documents_rejected(sp, reason or "")
            NotificationService.create_notification(
                recipient=student,
                verb="DOCUMENTS_REJECTED",
                message=f"Dokumenty k praxi '{practice_title}' byly zamítnuty." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif old_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.DOCUMENTS_REJECTED:
            NotificationService.create_notification(
                recipient=student,
                verb="DOCUMENTS_REJECTED",
                message=f"Finální dokumenty k praxi '{practice_title}' byly zamítnuty." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif (
            old_state == StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED
            and target_state == StudentPracticeWorkflowState.DOCUMENTS_REJECTED
        ):
            # T2c: review zamítlo opravné dokumenty → smyčka pokračuje
            NotificationService.create_notification(
                recipient=student,
                verb="DOCUMENTS_REJECTED",
                message=f"Opravné dokumenty k praxi '{practice_title}' byly zamítnuty." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif old_state == StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED and target_state in (
            StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
            StudentPracticeWorkflowState.ENDED,
        ):
            # T2c: review schválilo opravné dokumenty → pokračování cyklu
            NotificationService.create_notification(
                recipient=student,
                verb="DOCUMENTS_RESUBMITTED_APPROVED",
                message=f"Opravné dokumenty k praxi '{practice_title}' byly schváleny.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif old_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.COMPLETED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_COMPLETED",
                message=f"Praxe '{practice_title}' dokončena, zápočet udělen.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif old_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.REJECTED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_FAILED",
                message=f"Praxe '{practice_title}' nebyla úspěšně dokončena (Nesplněno).",
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif old_state == StudentPracticeWorkflowState.AWAITING_DOCUMENTS and target_state == StudentPracticeWorkflowState.CONTRACTED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_CONTRACTED",
                message=f"Smlouva k praxi '{practice_title}' byla potvrzena.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif old_state == StudentPracticeWorkflowState.AWAITING_CONTRACT and target_state == StudentPracticeWorkflowState.CONTRACTED:
            # notifikace organizaci o alokaci studenta (verb ALLOCATION_ORG)
            NotificationService.notify_org_allocation(sp)
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_CONTRACTED",
                message=f"Smlouva k praxi '{practice_title}' byla potvrzena.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )

        # Generic target-state-based notifications (fallback)
        elif target_state == StudentPracticeWorkflowState.PRELIMINARY_APPROVED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_PRE_APPROVED",
                message=f"Vaše přihláška na praxi '{practice_title}' byla předběžně schválena školou.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.REJECTED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_REJECTED",
                message=f"Vaše přihláška na praxi '{practice_title}' byla zamítnuta." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif target_state == StudentPracticeWorkflowState.CONTRACTED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_CONTRACTED",
                message=f"Vaše přihláška na praxi '{practice_title}' byla plně schválena. " f"Nyní nahrajte požadované dokumenty.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.STARTED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_STARTED",
                message=f"Vaše praxe '{practice_title}' byla spuštěna.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.COMPLETED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_COMPLETED",
                message=f"Vaše praxe '{practice_title}' byla úspěšně dokončena.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )

        return sp

    @staticmethod
    @transaction.atomic
    def process_invitation_approval(user, invitation_id, action):
        """
        Process the approval or rejection of an employer invitation.
        """
        try:
            invitation = EmployerInvitation.objects.select_for_update().get(invitation_id=invitation_id, user=user)
        except EmployerInvitation.DoesNotExist:
            raise ValueError(StudentPracticeMessages.INVITATION_NOT_FOUND)

        if invitation.status != EmployerInvitationStatus.PENDING:
            raise ValueError(StudentPracticeMessages.INVITATION_PROCESSED)

        if action == "accept":
            practice = invitation.practice

            # Uzámknutí parent praxe (stejný vzor jako apply_student_practice)
            # — všechny guardy běží PŘED označením pozvánky a vytvořením SP.
            if practice is not None:
                practice = Practice.objects.select_for_update().get(pk=practice.pk)

            # Validate practice is active and open for applications
            if not practice.is_active:
                raise ValueError(StudentPracticeMessages.PRACTICE_NOT_FOUND_OR_INACTIVE)
            if practice.workflow_state is not None and practice.workflow_state != PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                raise ValueError(StudentPracticeMessages.APPLICATIONS_CLOSED)

            # Capacity check — T2a: počítají se jen celková umístění
            if practice.available_positions is not None:
                active_count = StudentPractice.objects.filter(
                    practice=practice,
                    is_cancelled=False,
                    workflow_state__in=[
                        StudentPracticeWorkflowState.CONTRACTED,
                        StudentPracticeWorkflowState.STARTED,
                        StudentPracticeWorkflowState.ENDED,
                        StudentPracticeWorkflowState.COMPLETED,
                    ],
                ).count()
                if active_count >= practice.available_positions:
                    raise ValueError(StudentPracticeMessages.CAPACITY_FULL)

            # C03-A (finding 3): pending žádost/storno stejné registrace
            # (student+subject) blokuje přijetí pozvánky — stejná kanonická
            # hláška jako apply/reapply; žádná mutace při odmítnutí.
            if student_has_blocking_cancellation(user, practice):
                raise ValueError("Nelze podat novou žádost, dokud není storno vyřešeno")

            # Duplicate check
            if (
                StudentPractice.objects.filter(practice=practice, user=user, is_cancelled=False)
                .exclude(approval_status=ApprovalStatus.REJECTED)
                .exists()
            ):
                raise ValueError(StudentPracticeMessages.ALREADY_HAS_ACTIVE_APPLICATION)

            invitation.status = EmployerInvitationStatus.ACCEPTED
            invitation.save()

            try:
                student_practice = StudentPractice.objects.create(
                    user=user,
                    practice=practice,
                    application_date=date.today(),
                    workflow_state=StudentPracticeWorkflowState.APPLIED,
                    approval_status=ApprovalStatus.PENDING,  # Still pending school's approval
                    progress_status=ProgressStatus.NOT_STARTED,
                    hours_completed=0,
                    start_date=practice.start_date,
                    end_date=practice.end_date,
                    year=date.today().year,
                    employer_approved=True,
                    school_approved=False,
                    # BL-10/Q2-A: vazba na registraci předmětu (student, subject, year)
                    registration=ensure_practice_registration(user, practice.subject_id, date.today().year),
                )
            except IntegrityError:
                raise ValueError(StudentPracticeMessages.ALREADY_HAS_ACTIVE_APPLICATION)

            # Explicitly generate default documents
            DocumentHelper.assign_default_documents(student_practice)

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.INVITATION_ACCEPT,
                object_type="StudentPractice",
                object_id=student_practice.student_practice_id,
                description=f"Student {user.email} přijal pozvánku na praxi ID {invitation.practice_id}",
            )

            return {
                "detail": StudentPracticeMessages.INVITATION_ACCEPTED,
                "student_practice_id": student_practice.student_practice_id,
            }

        elif action == "reject":
            invitation.status = EmployerInvitationStatus.REJECTED
            invitation.save()

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.INVITATION_REJECT,
                object_type="EmployerInvitation",
                object_id=invitation.invitation_id,
                description=f"Student {user.email} odmítl pozvánku na praxi ID {invitation.practice_id}",
            )

            return {"detail": StudentPracticeMessages.INVITATION_REJECTED}

        raise ValueError(StudentPracticeMessages.INVALID_ACTION)

    @staticmethod
    @transaction.atomic
    def submit_cancellation_request(sp, actor, reason: str):
        """
        C02-A: student podává ŽÁDOST o storno — žádné okamžité storno.

        Praxe zůstává v aktuálním stavu (workflow_state, approval_status i
        is_cancelled beze změny). Důvod + ``cancellation_requested_at`` označí
        pending žádost; rozhodne resolver přes ``resolve_cancellation`` —
        okamžik rozhodnutí je okamžikem nevratnosti (C02-A/T2d).
        """
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)

        if sp.is_cancelled:
            raise ValueError(StudentPracticeMessages.ALREADY_CANCELLED)
        if sp.workflow_state == StudentPracticeWorkflowState.COMPLETED:
            raise ValueError("Storno nelze požadovat u již dokončené praxe (COMPLETED).")
        if not reason or not reason.strip():
            raise ValueError(StudentPracticeMessages.CANCELLATION_REASON_REQUIRED)
        if sp.cancellation_requested_at is not None and sp.cancellation_resolved_at is None:
            raise ValueError("Žádost o storno již byla podána a čeká na rozhodnutí.")

        old_state_name = sp.workflow_state.name if sp.workflow_state else "None"
        sp.cancellation_reason = reason.strip()
        sp.cancellation_requested_at = timezone.now()
        sp.save(update_fields=["cancellation_reason", "cancellation_requested_at"])

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATUS_CHANGE,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(f"Žádost o storno přihlášky ID {sp.student_practice_id} (stav zůstává {old_state_name}): {reason.strip()}"),
        )

        # in-app rozhodovatelům (garanti katedry — resolve-cancellation)
        recipients = NotificationService.resolve_garant_recipients(sp)
        student_name = sp.user.full_name if sp.user else ""
        practice_title = sp.practice.title if sp.practice else "N/A"
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="CANCELLATION_REQUESTED",
                message=(
                    f"Student {student_name} požádal o storno přihlášky na praxi "
                    f"'{practice_title}' — čeká na rozhodnutí. Důvod: {reason.strip()}"
                ),
                actor=actor,
                target=sp,
                notification_type=NotificationType.WARNING,
                send_email=False,
            )
        return sp

    @staticmethod
    @transaction.atomic
    def cancel_student_practice(sp, actor, reason: str):
        """
        Cancel (storno) a StudentPractice.

        Marks the practice as cancelled with full audit trail and sets
        the old-style statuses to REJECTED / CANCELLED respectively.
        """
        # Refetch with row lock to prevent race conditions
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)

        if sp.is_cancelled:
            raise ValueError(StudentPracticeMessages.ALREADY_CANCELLED)

        if sp.workflow_state == StudentPracticeWorkflowState.COMPLETED:
            raise ValueError("Storno nelze provést u již dokončené praxe (COMPLETED).")

        if not reason or not reason.strip():
            raise ValueError(StudentPracticeMessages.CANCELLATION_REASON_REQUIRED)

        # ulož původní název stavu do auditního záznamu
        old_state_name = sp.workflow_state.name if sp.workflow_state else "None"

        sp.is_cancelled = True
        sp.cancelled_at = timezone.now()
        sp.cancelled_by = actor
        sp.cancellation_reason = reason.strip()

        sp.approval_status = ApprovalStatus.REJECTED
        sp.progress_status = ProgressStatus.CANCELLED

        # CR: Mark workflow as cancelled — use is_cancelled flag to derive status
        # (is_cancelled=True takes precedence over workflow_state in workflow_status property)
        sp.workflow_state = None

        sp.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STORNO,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(f"Stornovana prihlaska ID {sp.student_practice_id}: {reason.strip()} " f"(původní stav: {old_state_name})"),
        )

        # --- Notify student ---
        if sp.user:
            NotificationService.create_notification(
                recipient=sp.user,
                verb="APPLICATION_CANCELLED",
                message=f"Vaše přihláška na praxi '{sp.practice.title}' byla zrušena. Důvod: {reason.strip()}",
                actor=actor,
                target=sp,
                notification_type=NotificationType.WARNING,
                send_email=False,
            )

        # --- Notify org contact if applicable ---
        practice = sp.practice
        org_contact = getattr(practice, "contact_user", None) if practice else None
        if org_contact:
            student_name = sp.user.full_name if sp.user else "Neznámý student"
            NotificationService.create_notification(
                recipient=org_contact,
                verb="APPLICATION_CANCELLED_ORG",
                message=f"Přihláška studenta {student_name} na praxi '{sp.practice.title}' byla zrušena. " f"Důvod: {reason.strip()}",
                actor=actor,
                target=sp,
                notification_type=NotificationType.WARNING,
                send_email=False,
            )

        # --- Send email notifications ---
        if sp.user:
            EmailService.notify_student_cancellation(sp.user, sp, reason.strip())
        if org_contact and practice and practice.employer:
            EmailService.notify_org_cancellation(practice.employer, sp, reason.strip())

        # --- notifikace garantovi (verb CANCELLATION_GARANT) ---
        NotificationService.notify_garant_cancellation(sp)

        return sp

    @staticmethod
    @transaction.atomic
    def transition_to_awaiting_documents_after_contract_upload(sp, actor):
        """
        po úspěšném nahrání smluvního dokumentu (typ CONTRACT)
        ze stavu AWAITING_CONTRACT automaticky přechod do AWAITING_DOCUMENTS
        (atomicky + ActionLog). Student nemá roli na state machine přechod —
        proto se provádí zde, v upload endpointu.
        """
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
        if sp.is_cancelled or sp.workflow_state != StudentPracticeWorkflowState.AWAITING_CONTRACT:
            return sp

        old_state = sp.workflow_state
        sp.workflow_state = StudentPracticeWorkflowState.AWAITING_DOCUMENTS
        sp.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Automaticky prechod po uploadu smluvniho dokumentu ID "
                f"{sp.student_practice_id}: {old_state.name} -> "
                f"{StudentPracticeWorkflowState.AWAITING_DOCUMENTS.name}"
            ),
        )

        student = sp.user
        practice_title = sp.practice.title if sp.practice else "N/A"
        EmailService.notify_student_awaiting_documents(sp)
        if student:
            NotificationService.create_notification(
                recipient=student,
                verb="AWAITING_DOCUMENTS",
                message=f"Žádáme o nahrání dokumentů k praxi '{practice_title}'.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.INFO,
            )

        return sp

    @staticmethod
    @transaction.atomic
    def resolve_cancellation(sp, actor, decision: str | None = None):
        """
        Rozhodnutí o stornu / žádosti o storno (T2d, C02-A, C03-A).

        - Legacy větev (``is_cancelled=True``, ještě nevyřešeno — např. kaskáda
          zrušení praxe): jen ``cancellation_resolved_at`` — odblokování,
          chování se nemění.
        - C02-A pending žádost (``cancellation_requested_at`` + nevyřešeno):
          rozhodnutí je OKAMŽIK NEVRATNOSTI. ``decision="approve"`` → storno
          se provede nyní (nevratné) + resolved; ``decision="reject"`` →
          žádost zamítnuta, praxe zůstává aktivní + resolved; bez/neplatný
          decision → 400 (povinné rozhodnutí).
        """
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)

        # --- Legacy: již stornované (okamžité) — jen odblokovat ---
        if sp.is_cancelled:
            if sp.cancellation_resolved_at is not None:
                raise ValueError("Storno je již vyřešeno.")
            sp.cancellation_resolved_at = timezone.now()
            sp.save(update_fields=["cancellation_resolved_at"])
            ActionLogService.log(
                user=actor,
                action_type=ActionLogType.STATUS_CHANGE,
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
                description=(
                    f"Vyřešení storna přihlášky ID {sp.student_practice_id} "
                    f"uživatelem {actor.email if getattr(actor, 'email', None) else actor}"
                ),
            )
            return sp

        # --- C02-A: pending žádost o storno ---
        pending_request = sp.cancellation_requested_at is not None and sp.cancellation_resolved_at is None
        if pending_request and sp.cancellation_reason:
            if decision not in ("approve", "reject"):
                raise ValueError("Pro rozhodnutí o žádosti o storno je povinné pole decision=approve|reject.")

            if decision == "approve":
                # Okamžik nevratnosti (C02-A): platí se storno.
                sp = StudentPracticeService.cancel_student_practice(sp=sp, actor=actor, reason=sp.cancellation_reason)
                sp.cancellation_resolved_at = timezone.now()
                sp.save(update_fields=["cancellation_resolved_at"])
                ActionLogService.log(
                    user=actor,
                    action_type=ActionLogType.STATUS_CHANGE,
                    object_type="StudentPractice",
                    object_id=sp.student_practice_id,
                    description=(
                        f"Schválení žádosti o storno přihlášky ID {sp.student_practice_id} "
                        f"uživatelem {actor.email if getattr(actor, 'email', None) else actor} — storno provedeno"
                    ),
                )
                return sp

            # decision == "reject" — žádost zamítnuta, praxe zůstává aktivní
            sp.cancellation_resolved_at = timezone.now()
            sp.save(update_fields=["cancellation_resolved_at"])
            ActionLogService.log(
                user=actor,
                action_type=ActionLogType.STATUS_CHANGE,
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
                description=(
                    f"Zamítnutí žádosti o storno přihlášky ID {sp.student_practice_id} "
                    f"uživatelem {actor.email if getattr(actor, 'email', None) else actor} — praxe zůstává aktivní"
                ),
            )
            if sp.user:
                NotificationService.create_notification(
                    recipient=sp.user,
                    verb="CANCELLATION_REQUEST_REJECTED",
                    message=(f"Vaše žádost o storno přihlášky na praxi '{sp.practice.title if sp.practice else 'N/A'}' byla zamítnuta."),
                    actor=actor,
                    target=sp,
                    notification_type=NotificationType.INFO,
                    send_email=False,
                )
            return sp

        raise ValueError("Přihláška není stornovaná — není co řešit.")

    @staticmethod
    @transaction.atomic
    def reapply_to_practice(student, practice_id: int):
        """
        Re-apply a student to a practice (creates a fresh StudentPractice).

        Validates that the practice exists, is active, not cancelled,
        accepting applications, has capacity, and that the student does
        not already have an active (non-cancelled, non-rejected) application.
        """
        # Refetch practice with row lock to prevent capacity race conditions
        practice = Practice.objects.select_for_update().filter(practice_id=practice_id).first()
        if not practice or not practice.is_active:
            raise ValueError(StudentPracticeMessages.PRACTICE_NOT_FOUND_OR_INACTIVE)

        if practice.is_cancelled:
            raise ValueError(StudentPracticeMessages.PRACTICE_CANCELLED)

        if practice.workflow_state is not None and practice.workflow_state != PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
            raise ValueError(StudentPracticeMessages.APPLICATIONS_CLOSED)

        # nevyřešené storno NEBO pending žádost o storno blokuje novou žádost
        # pro stejnou registraci (C03-A; shodná kontrola jako v
        # practices/services.py apply_student_practice).
        if student_has_blocking_cancellation(student, practice):
            # Kanonická hláška — stejná jako v apply_student_practice.
            raise ValueError("Nelze podat novou žádost, dokud není storno vyřešeno")

        # Reject if an active (non-cancelled, non-rejected) StudentPractice already exists
        existing = (
            StudentPractice.objects.filter(
                user=student,
                practice=practice,
                is_cancelled=False,
            )
            .exclude(
                approval_status=ApprovalStatus.REJECTED,
            )
            .first()
        )
        if existing is not None:
            raise ValueError(StudentPracticeMessages.ALREADY_HAS_ACTIVE_APPLICATION)

        # Check capacity — T2a: počítají se jen celková umístění
        if practice.available_positions is not None:
            active_count = StudentPractice.objects.filter(
                practice=practice,
                is_cancelled=False,
                workflow_state__in=[
                    StudentPracticeWorkflowState.CONTRACTED,
                    StudentPracticeWorkflowState.STARTED,
                    StudentPracticeWorkflowState.ENDED,
                    StudentPracticeWorkflowState.COMPLETED,
                ],
            ).count()
            if active_count >= practice.available_positions:
                raise ValueError(StudentPracticeMessages.CAPACITY_FULL)

        sp = StudentPractice.objects.create(
            user=student,
            practice=practice,
            application_date=date.today(),
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            hours_completed=0,
            year=date.today().year,
            start_date=practice.start_date,
            end_date=practice.end_date,
            # BL-10/Q2-A: vazba na registraci předmětu (student, subject, year)
            registration=ensure_practice_registration(student, practice.subject_id, date.today().year),
        )

        DocumentHelper.assign_default_documents(sp)

        ActionLogService.log(
            user=student,
            action_type=ActionLogType.APPLY,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Student {student.email} se znovu prihlasil na praxi ID {practice_id} " f"(nova prihlaska ID {sp.student_practice_id})"
            ),
        )

        return sp

    @staticmethod
    @transaction.atomic
    def process_document_review(user, document_id: int, status_val: int, review_note: str = ""):
        """
        Allows a professor or admin to approve or reject a document.
        """
        from student_practices.models import UploadedDocument

        document = UploadedDocument.objects.select_for_update().get(pk=document_id)
        student_practice = document.student_practice

        if not student_practice:
            raise ValueError(StudentPracticeMessages.NOT_FOUND)

        roles = can_manage_practice(user, student_practice)
        if not (roles["is_professor"] or roles["is_admin"]):
            raise PermissionDenied()

        valid_statuses = [s.value for s in DocumentStatus]
        if status_val not in valid_statuses:
            raise ValueError(StudentPracticeMessages.INVALID_APPROVAL_VALUE)

        document.status = status_val
        document.review_note = review_note
        document.save()

        EmailService.notify_student_document_review(document)

        status_label_cz = "schválen" if status_val == DocumentStatus.APPROVED else "zamítnut"
        NotificationService.create_notification(
            recipient=student_practice.user,
            verb="DOCUMENT_REVIEWED",
            message=f"Váš dokument '{document.document_type.name.lower()}' k praxi "
            f"'{student_practice.practice.title}' byl {status_label_cz}." + (f" Důvod: {review_note}" if review_note else ""),
            actor=user,
            target=document,
            notification_type=NotificationType.SUCCESS if status_val == DocumentStatus.APPROVED else NotificationType.ERROR,
        )

        status_label = "schválen" if status_val == DocumentStatus.APPROVED else "zamítnut"
        ActionLogService.log(
            user=user,
            action_type=ActionLogType.DOCUMENT_REVIEW,
            object_type="UploadedDocument",
            object_id=document.pk,
            description=f"Dokument {document.document_type} {status_label} uživatelem {user.email}",
        )

        # CONTRACT dokumenty řídí stav StudentPractice.
        #   - kterýkoli CONTRACT dokument REJECTED → DOCUMENTS_REJECTED (s rejection_reason)
        #   - všechny CONTRACT dokumenty APPROVED → CONTRACTED (NE auto-STARTED —
        #     STARTED řeší jen cron auto_start_end_practices dle data)
        if document.document_type == DocumentType.CONTRACT:
            if status_val == DocumentStatus.REJECTED:
                StudentPracticeService._apply_document_rejection_state(student_practice, user, review_note)
            elif status_val == DocumentStatus.APPROVED:
                StudentPracticeService._apply_document_approval_state(student_practice, user)
        elif (
            student_practice.workflow_state == StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED and status_val == DocumentStatus.REJECTED
        ):
            # C19-B/T2c (finding 5): review zamítne opravený (ne-smluvní)
            # dokument → zpět do DOCUMENTS_RESUBMITTED→DOCUMENTS_REJECTED smyčky.
            # APPROVED zde zůstává bez postupu — konečné rozhodnutí je výslovný
            # transition s preconditionem schváleného dokumentu (explicit separation).
            StudentPracticeService._apply_document_rejection_state(student_practice, user, review_note)

        return document

    @staticmethod
    @transaction.atomic
    def _apply_document_rejection_state(sp, actor, review_note: str):
        """Kterýkoli dokument REJECTED → DOCUMENTS_REJECTED (s rejection_reason).

        Stavy: AWAITING_DOCUMENTS / ENDED (původní zamítnutí) a
        DOCUMENTS_RESUBMITTED (C19-B/T2c: review zamítlo opravu → zpět do smyčky).
        """
        if sp.workflow_state not in (
            StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
            StudentPracticeWorkflowState.ENDED,
            StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED,
        ):
            return

        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
        if sp.is_cancelled or sp.workflow_state not in (
            StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
            StudentPracticeWorkflowState.ENDED,
            StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED,
        ):
            return

        old_state = sp.workflow_state
        sp.workflow_state = StudentPracticeWorkflowState.DOCUMENTS_REJECTED
        if review_note:
            sp.rejection_reason = review_note
        sp.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Zamítnutí dokumentů převedlo praxi ID {sp.student_practice_id}: "
                f"{old_state.name} -> {StudentPracticeWorkflowState.DOCUMENTS_REJECTED.name}"
            ),
        )

        practice_title = sp.practice.title if sp.practice else "N/A"
        EmailService.notify_student_documents_rejected(sp, review_note or "")
        if sp.user:
            NotificationService.create_notification(
                recipient=sp.user,
                verb="DOCUMENTS_REJECTED",
                message=f"Dokumenty k praxi '{practice_title}' byly zamítnuty." + (f" Důvod: {review_note}" if review_note else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )

    @staticmethod
    @transaction.atomic
    def _apply_document_approval_state(sp, actor):
        """
        Schválení CONTRACT dokumentu ve AWAITING_DOCUMENTS.

        T1/C06-A (finding 1): review zapisuje JEN vlastní (školní) osu
        aktéra — do CONTRACTED postupuje POUZE pokud obě nezávislé osy
        drží; jinak SP zůstává ve AWAITING_DOCUMENTS s vlastní osou
        zapsanou (cizí osu tento review nikdy nenastaví). Kapacita (T2a)
        běží pod stejným lockem. STARTED řeší jen cron auto_start_end_practices.
        """
        if sp.workflow_state != StudentPracticeWorkflowState.AWAITING_DOCUMENTS:
            return
        if not (sp.contract_document and sp.contract_document.status == DocumentStatus.APPROVED):
            return

        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
        if sp.is_cancelled or sp.workflow_state != StudentPracticeWorkflowState.AWAITING_DOCUMENTS:
            return
        if not (sp.contract_document and sp.contract_document.status == DocumentStatus.APPROVED):
            return

        # T1: zápis jen vlastní osy; bez obou os → žádný postup, žádná notifikace.
        both_axes = record_own_approval_axis(sp, actor)
        if not both_axes:
            sp.save(update_fields=["school_approved", "employer_approved"])
            logger.info(
                "T1: SP %s zůstává ve AWAITING_DOCUMENTS — chybí druhá schvalovací osa (review nepostupuje).",
                sp.student_practice_id,
            )
            return

        # T2a/BE-005: alokace MUSÍ projít kapacitní kontrolou (select_for_update
        # na praxi uvnitř transakce). Při plné kapacitě se přechod NEPROVEDE —
        # tichý skip: dokument zůstává schválen, SP čeká ve AWAITING_DOCUMENTS.
        if sp.practice_id:
            locked_practice = Practice.objects.select_for_update().get(pk=sp.practice_id)
            try:
                _check_contract_capacity(locked_practice)
            except ValueError:
                logger.warning(
                    "CAPACITY_FULL: schválení smlouvy nepřevedlo SP %s na CONTRACTED (kapacita naplněna).",
                    sp.student_practice_id,
                )
                return

        old_state = sp.workflow_state
        sp.workflow_state = StudentPracticeWorkflowState.CONTRACTED
        sp.approval_status = ApprovalStatus.APPROVED
        sp.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Schválení smluvních dokumentů převedlo praxi ID {sp.student_practice_id}: "
                f"{old_state.name} -> {StudentPracticeWorkflowState.CONTRACTED.name}"
            ),
        )

        practice_title = sp.practice.title if sp.practice else "N/A"
        if sp.user:
            NotificationService.create_notification(
                recipient=sp.user,
                verb="APPLICATION_CONTRACTED",
                message=f"Smlouva k praxi '{practice_title}' byla potvrzena.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        # alokace studenta → notifikace organizaci (in-app + e-mail)
        NotificationService.notify_org_allocation(sp)

    @staticmethod
    @transaction.atomic
    def mark_documents_resubmitted_for_review(sp, actor):
        """
        C19-B/T2c: po úspěšném nahrání opravených dokumentů ze stavu
        DOCUMENTS_REJECTED → DOCUMENTS_RESUBMITTED (explicitní review-pending).

        Upload NIKDY neznamená schválení — review (garant/škola) rozhodne
        o dalším stavu přes transition endpoint; smyčka je neomezená.

        Finding 2: hrana DOCUMENTS_REJECTED → DOCUMENTS_RESUBMITTED je
        POUZE čin vlastníka-studenta (T2c „student resubmit") — ověřeno
        znovu na uzamčeném SP; ostatní oprávnění uploadéři (organizace,
        pedagog) doklad nahrají, ale stav se neposune.
        """
        sp = StudentPractice.objects.select_for_update().get(pk=sp.pk)
        if sp.is_cancelled or sp.workflow_state != StudentPracticeWorkflowState.DOCUMENTS_REJECTED:
            return sp

        # Ownership guard: jen vlastník SP (StudentUser, sp.user == actor)
        # smí přepnout stav do review-pending; cizí/neroli aktér → žádná mutace.
        if not (isinstance(actor, StudentUser) and sp.user_id == actor.pk):
            # MINOR (round 3): jen necitlivý výsledek/role + opaque ID —
            # žádný e-mail ani repr objektu do logu.
            logger.info(
                "Repair-resubmit přeskočen pro SP %s — aktér není vlastník-student (role=%s).",
                sp.student_practice_id,
                type(actor).__name__,
            )
            return sp

        old_state = sp.workflow_state
        sp.workflow_state = StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED
        sp.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(
                f"Nahrazení zamítnutých dokumentů — čeká na review: "
                f"{old_state.name} -> {StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED.name}"
            ),
        )

        # in-app: garanti/přiřazený vyučující = rozhodovatelé review
        recipients = NotificationService.resolve_garant_recipients(sp)
        student_name = sp.user.full_name if sp.user else ""
        practice_title = sp.practice.title if sp.practice else "N/A"
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                verb="DOCUMENTS_RESUBMITTED",
                message=(f"Student {student_name} nahradil zamítnuté dokumenty k praxi '{practice_title}' a čeká na review."),
                actor=actor,
                target=sp,
                notification_type=NotificationType.INFO,
                send_email=False,
            )
        return sp


# ===================================================================
# Document generation services (STAG + template engine)
# ===================================================================


def _get_student_display_name(student: StudentUser) -> str:
    """Build a full display name from student fields."""
    parts = []
    if getattr(student, "title_before", ""):
        parts.append(student.title_before)
    parts.append(student.first_name)
    parts.append(student.last_name)
    if getattr(student, "title_after", ""):
        parts.append(student.title_after)
    return " ".join(parts)


def _get_student_address(student: StudentUser) -> str:
    """Build a formatted address string from student fields."""
    if student.street:
        base = f"{student.street}"
        if student.street_number:
            base += f" {student.street_number}"
        if student.zip_code or student.city:
            base += ","
        if student.zip_code:
            base += f" {student.zip_code}"
        if student.city:
            base += f" {student.city}"
        return base
    return ""


def _format_date(d: date | None) -> str:
    """Format a date as 'dd. mm. yyyy' or empty string."""
    if d is None:
        return ""
    return d.strftime("%d. %m. %Y")


# STAG data cache to avoid repeated API calls within the same process lifetime
_stag_data_cache = {}


def generate_contract(sp: StudentPractice) -> io.BytesIO:
    """
    Generate a Czech internship contract (.docx) for a StudentPractice.

    Fetches fresh STAG student data, combines with practice + employer info,
    and returns a BytesIO buffer ready for download.

    Returns:
        io.BytesIO containing the generated .docx document.
    """
    if not sp.user:
        raise ValueError("StudentPractice has no associated student")

    student: StudentUser = sp.user
    practice: Practice = sp.practice

    # Ensure we have the latest STAG data (cached by os_cislo)
    cache_key = student.os_cislo
    if cache_key and cache_key not in _stag_data_cache:
        try:
            fetch_student_data_from_stag(student)
        except Exception:
            pass  # Non-critical — use whatever data we have
        if cache_key:
            _stag_data_cache[cache_key] = True

    student_name = _get_student_display_name(student)
    student_birth_date = _format_date(student.date_of_birth)
    student_birth_place = student.place_of_birth or ""
    student_address = _get_student_address(student)
    student_email = student.email or ""
    student_phone = student.phone or ""
    student_os_cislo = student.os_cislo or ""
    student_field = student.field_of_study or ""
    student_year = student.year_of_study or 0

    # Employer info — handle both registered and external employers
    if practice.is_external and practice.external_employer:
        ext = practice.external_employer
        employer_name = ext.name
        employer_address = ext.address or ""
        employer_ico = ext.ico or ""
        employer_contact = ext.contact_name or ""
        employer_email = ext.contact_email or ""
    elif practice.employer:
        emp = practice.employer
        employer_name = emp.company_name or ""
        employer_address = emp.address or ""
        employer_ico = emp.ico or ""
        contact_user = practice.contact_user
        employer_contact = contact_user.full_name if contact_user else emp.company_name
        employer_email = contact_user.email if contact_user else ""
    else:
        employer_name = "N/A"
        employer_address = ""
        employer_ico = ""
        employer_contact = ""
        employer_email = ""

    # Practice details
    practice_title = practice.title or ""
    practice_description = practice.description or ""
    practice_start = _format_date(practice.start_date)
    practice_end = _format_date(practice.end_date)
    practice_hours = practice.subject.min_hours if practice.subject else 480

    # Subject info
    subject_name = practice.subject.subject_name if practice.subject else ""
    subject_code = practice.subject.subject_code if practice.subject else ""

    return ContractGenerator.generate(
        student_name=student_name,
        student_birth_date=student_birth_date,
        student_birth_place=student_birth_place,
        student_address=student_address,
        student_email=student_email,
        student_phone=student_phone,
        student_os_cislo=student_os_cislo,
        student_field=student_field,
        student_year=student_year,
        employer_name=employer_name,
        employer_address=employer_address,
        employer_ico=employer_ico,
        employer_contact=employer_contact,
        employer_email=employer_email,
        practice_title=practice_title,
        practice_description=practice_description,
        practice_start_date=practice_start,
        practice_end_date=practice_end,
        practice_hours=practice_hours,
        subject_name=subject_name,
        subject_code=subject_code,
    )


def generate_content_document(sp: StudentPractice) -> io.BytesIO:
    """Generate a work content description (Pracovní náplň) for a StudentPractice."""
    if not sp.practice:
        raise ValueError("StudentPractice has no associated practice")
    return ContentGenerator.generate(
        title=sp.practice.title or "Odborná praxe",
        description=sp.practice.description or "",
        responsibilities=sp.practice.responsibilities or "",
        hours=sp.practice.subject.min_hours if sp.practice.subject else 480,
    )


def generate_report(sp: StudentPractice) -> io.BytesIO:
    """Generate a practice report/log (Výkaz odborné praxe) for a StudentPractice."""
    if not sp.user:
        raise ValueError("StudentPractice has no associated student")
    student = sp.user
    return ReportGenerator.generate(
        student_name=_get_student_display_name(student) if student else "—",
        practice_title=sp.practice.title or "Odborná praxe",
        start_date=_format_date(sp.start_date),
        end_date=_format_date(sp.end_date),
        hours=sp.practice.subject.min_hours if sp.practice.subject else 480,
    )


def generate_feedback_form(sp: StudentPractice) -> io.BytesIO:
    """Generate a practice evaluation form (Hodnocení odborné praxe) for a StudentPractice."""
    if not sp.user:
        raise ValueError("StudentPractice has no associated student")
    student = sp.user
    return FeedbackGenerator.generate(
        student_name=_get_student_display_name(student) if student else "—",
        practice_title=sp.practice.title or "Odborná praxe",
    )
