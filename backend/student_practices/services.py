import io
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
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus, StudentUser
from users.services import fetch_student_data_from_stag

SP_TRANSITIONS = {
    StudentPracticeWorkflowState.APPLIED: [
        StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.PRELIMINARY_APPROVED: [
        StudentPracticeWorkflowState.CONTRACTED,
        StudentPracticeWorkflowState.REJECTED,
    ],
    StudentPracticeWorkflowState.CONTRACTED: [
        StudentPracticeWorkflowState.STARTED,
    ],
    StudentPracticeWorkflowState.STARTED: [
        StudentPracticeWorkflowState.ENDED,
    ],
    StudentPracticeWorkflowState.ENDED: [
        StudentPracticeWorkflowState.COMPLETED,
    ],
}


class StudentPracticeService:
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

        # Only allow initialization from None to APPLIED
        if sp.workflow_state is None:
            if target_state != StudentPracticeWorkflowState.APPLIED:
                raise ValueError(f"Neinicializovana prihlaska — povolen je pouze prechod do APPLIED, " f"ne do {target_state.name}")

        allowed = SP_TRANSITIONS.get(sp.workflow_state)
        if sp.workflow_state is not None and allowed is None:
            raise ValueError(StudentPracticeMessages.TRANSITION_NOT_DEFINED.format(sp.workflow_state))

        if sp.is_cancelled:
            raise ValueError(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY)

        if sp.workflow_state is not None and target_state not in allowed:
            raise ValueError(StudentPracticeMessages.TRANSITION_NOT_ALLOWED.format(sp.workflow_state, target_state))

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

            sp.school_approved = True
            sp.employer_approved = True
            sp.approval_status = ApprovalStatus.APPROVED

        elif sp.workflow_state == StudentPracticeWorkflowState.CONTRACTED and target_state == StudentPracticeWorkflowState.STARTED:
            sp.progress_status = ProgressStatus.IN_PROGRESS

        elif sp.workflow_state == StudentPracticeWorkflowState.ENDED and target_state == StudentPracticeWorkflowState.COMPLETED:
            sp.progress_status = ProgressStatus.COMPLETED

        # --- Apply new workflow state ---
        old_state = sp.workflow_state
        sp.workflow_state = target_state
        sp.save()

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
        if target_state == StudentPracticeWorkflowState.PRELIMINARY_APPROVED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_PRE_APPROVED",
                message=f"Vaše přihláška na praxi '{sp.practice.title}' byla předběžně schválena školou.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.REJECTED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_REJECTED",
                message=f"Vaše přihláška na praxi '{sp.practice.title}' byla zamítnuta." + (f" Důvod: {reason}" if reason else ""),
                actor=actor,
                target=sp,
                notification_type=NotificationType.ERROR,
            )
        elif target_state == StudentPracticeWorkflowState.CONTRACTED:
            NotificationService.create_notification(
                recipient=student,
                verb="APPLICATION_CONTRACTED",
                message=f"Vaše přihláška na praxi '{sp.practice.title}' byla plně schválena. " f"Nyní nahrajte požadované dokumenty.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.STARTED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_STARTED",
                message=f"Vaše praxe '{sp.practice.title}' byla spuštěna.",
                actor=actor,
                target=sp,
                notification_type=NotificationType.SUCCESS,
            )
        elif target_state == StudentPracticeWorkflowState.COMPLETED:
            NotificationService.create_notification(
                recipient=student,
                verb="PRACTICE_COMPLETED",
                message=f"Vaše praxe '{sp.practice.title}' byla úspěšně dokončena.",
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
            invitation.status = EmployerInvitationStatus.ACCEPTED
            invitation.save()

            practice = invitation.practice

            # Validate practice is active and open for applications
            if not practice.is_active:
                raise ValueError(StudentPracticeMessages.PRACTICE_NOT_FOUND_OR_INACTIVE)
            if practice.workflow_state is not None and practice.workflow_state != PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                raise ValueError(StudentPracticeMessages.APPLICATIONS_CLOSED)

            # Capacity check
            if practice.available_positions is not None and practice.available_positions > 0:
                active_count = (
                    StudentPractice.objects.filter(
                        practice=practice,
                        is_cancelled=False,
                    )
                    .exclude(
                        approval_status=ApprovalStatus.REJECTED,
                    )
                    .count()
                )
                if active_count >= practice.available_positions:
                    raise ValueError(StudentPracticeMessages.CAPACITY_FULL)

            # Duplicate check
            if (
                StudentPractice.objects.filter(practice=practice, user=user, is_cancelled=False)
                .exclude(approval_status=ApprovalStatus.REJECTED)
                .exists()
            ):
                raise ValueError(StudentPracticeMessages.ALREADY_HAS_ACTIVE_APPLICATION)

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

        if not reason or not reason.strip():
            raise ValueError(StudentPracticeMessages.CANCELLATION_REASON_REQUIRED)

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
            description=(f"Stornovana prihlaska ID {sp.student_practice_id}: {reason.strip()}"),
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
            )

        # --- Send email notifications ---
        if sp.user:
            EmailService.notify_student_cancellation(sp.user, sp, reason.strip())
        if org_contact and practice and practice.employer:
            EmailService.notify_org_cancellation(practice.employer, sp, reason.strip())

        return sp

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

        # Check capacity
        if practice.available_positions is not None:
            active_count = (
                StudentPractice.objects.filter(
                    practice=practice,
                    is_cancelled=False,
                )
                .exclude(
                    approval_status=ApprovalStatus.REJECTED,
                )
                .count()
            )
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
    def update_student_practice_status(user, student_practice_id: int, data: dict):
        """
        Updates the status of a StudentPractice with transaction safety (select_for_update)
        to handle dual approval correctly.
        """
        try:
            student_practice = StudentPractice.objects.select_for_update().get(pk=student_practice_id)
        except StudentPractice.DoesNotExist:
            raise ValueError(StudentPracticeMessages.NOT_FOUND)

        if student_practice.is_cancelled:
            raise ValueError(StudentPracticeMessages.CANCELLED_CANNOT_MODIFY)

        old_status = student_practice.approval_status
        old_workflow_state = student_practice.workflow_state

        roles = can_manage_practice(user, student_practice)
        is_professor = roles["is_professor"]
        is_org = roles["is_org"]
        is_admin = roles["is_admin"]

        # 1. Handle dual approval_status update
        if "approval_status" in data:
            try:
                new_val = int(data["approval_status"])
            except (ValueError, TypeError):
                raise ValueError(StudentPracticeMessages.INVALID_APPROVAL_VALUE)

            if new_val == ApprovalStatus.APPROVED:
                # Set flags based on authorized roles
                if is_professor or is_admin:
                    student_practice.school_approved = True
                if is_org or is_admin:
                    student_practice.employer_approved = True

                # Fully approve only if BOTH parties approved
                if student_practice.school_approved and student_practice.employer_approved:
                    student_practice.approval_status = ApprovalStatus.APPROVED
                    # WE REMOVED AUTO-START HERE.
                    # The practice will only start when documents are also approved.
                else:
                    student_practice.approval_status = ApprovalStatus.PENDING

            elif new_val == ApprovalStatus.REJECTED:
                # Either party can reject immediately
                if is_professor or is_org or is_admin:
                    student_practice.approval_status = ApprovalStatus.REJECTED
                    # Note: potentially reset flags? Usually REJECTED is final.
                else:
                    raise ValueError(StudentPracticeMessages.CANNOT_REJECT)

            # --- Workflow state mapping from dual approval ---
            # Determine the target workflow state
            if student_practice.approval_status == ApprovalStatus.REJECTED:
                target_wf = StudentPracticeWorkflowState.REJECTED
            elif student_practice.school_approved and student_practice.employer_approved:
                target_wf = StudentPracticeWorkflowState.CONTRACTED
            elif student_practice.school_approved or student_practice.employer_approved:
                target_wf = StudentPracticeWorkflowState.PRELIMINARY_APPROVED
            else:
                target_wf = StudentPracticeWorkflowState.APPLIED

            # Don't regress workflow_state if already at a more advanced state
            current_wf = student_practice.workflow_state
            if current_wf is not None:
                if target_wf.value < current_wf.value and target_wf != StudentPracticeWorkflowState.REJECTED:
                    raise ValueError("Nelze vracet stav niz nez aktualni")

            student_practice.workflow_state = target_wf
            # If neither approved, leave workflow_state as APPLIED (initial state)

        # 2. Handle progress_status update (only after full approval)
        if "progress_status" in data:
            if student_practice.approval_status != ApprovalStatus.APPROVED and not is_admin:
                raise ValueError(StudentPracticeMessages.PROGRESS_UPDATE_FORBIDDEN)

            try:
                student_practice.progress_status = int(data["progress_status"])
            except (ValueError, TypeError):
                raise ValueError(StudentPracticeMessages.INVALID_PROGRESS_VALUE)

            # --- Workflow state mapping from progress_status ---
            if student_practice.progress_status == ProgressStatus.IN_PROGRESS:
                if student_practice.workflow_state == StudentPracticeWorkflowState.CONTRACTED:
                    student_practice.workflow_state = StudentPracticeWorkflowState.STARTED
            elif student_practice.progress_status == ProgressStatus.COMPLETED:
                student_practice.workflow_state = StudentPracticeWorkflowState.COMPLETED

        # 3. Handle other fields (hours_completed, notes, etc.)
        if "hours_completed" in data:
            hours = data.get("hours_completed")
            if hours is not None:
                if not isinstance(hours, int) or hours < 0:
                    raise ValueError("Hodnota hours_completed musi byt nezaporne cele cislo")
                student_practice.hours_completed = hours

        student_practice.save()

        if student_practice.approval_status != old_status:
            EmailService.notify_student_application_status(student_practice)
            NotificationService.create_notification(
                recipient=student_practice.user,
                verb="APPLICATION_STATUS_CHANGED",
                message=f"Stav vaší přihlášky na praxi '{student_practice.practice.title}' "
                f"byl změněn na '{student_practice.approval_status.name}'.",
                actor=user,
                target=student_practice,
                notification_type=NotificationType.INFO,
            )

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.STATUS_CHANGE,
            object_type="StudentPractice",
            object_id=student_practice.student_practice_id,
            description=(
                f"Změna stavu přihlášky ID {student_practice.student_practice_id} "
                f"uživatelem {user.email} (data: {data}), "
                f"workflow_state: {old_workflow_state.name if old_workflow_state else 'None'} -> "
                f"{student_practice.workflow_state.name if student_practice.workflow_state else 'None'}"
            ),
        )

        return student_practice

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

        # Try to auto-start practice if everything is ready
        StudentPracticeService.evaluate_practice_readiness(student_practice)

        return document

    @staticmethod
    def evaluate_practice_readiness(student_practice):
        """
        Checks if the practice can transition to IN_PROGRESS.
        Requires:
        1. approval_status == APPROVED
        2. contract_document.status == APPROVED
        3. content_document.status == APPROVED
        """
        if student_practice.approval_status == ApprovalStatus.APPROVED and student_practice.progress_status == ProgressStatus.NOT_STARTED:
            # Check mandatory documents
            contract_ok = student_practice.contract_document and student_practice.contract_document.status == DocumentStatus.APPROVED
            content_ok = student_practice.content_document and student_practice.content_document.status == DocumentStatus.APPROVED

            if contract_ok and content_ok:
                student_practice.progress_status = ProgressStatus.IN_PROGRESS
                student_practice.workflow_state = StudentPracticeWorkflowState.STARTED
                student_practice.save()

                NotificationService.create_notification(
                    recipient=student_practice.user,
                    verb="PRACTICE_STARTED",
                    message=f"Vaše praxe '{student_practice.practice.title}' byla automaticky spuštěna " f"po schválení všech dokumentů.",
                    actor=None,
                    target=student_practice,
                    notification_type=NotificationType.SUCCESS,
                )

                ActionLogService.log(
                    user=None,
                    action_type=ActionLogType.STATUS_CHANGE,
                    object_type="StudentPractice",
                    object_id=student_practice.student_practice_id,
                    description=f"Praxe automaticky spuštěna (ID: {student_practice.student_practice_id})",
                )


# ===================================================================
# WP7: Document generation services (STAG + template engine)
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
