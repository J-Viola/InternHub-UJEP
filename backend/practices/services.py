import base64
import mimetypes
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from notifications.models import NotificationType
from notifications.services import EmailService, NotificationService

from practices.messages import PracticeMessages
from practices.models import (
    ApplicationClosureReason,
    Practice,
    PracticeWorkflowState,
    ProgressStatus,
)
from student_practices.models import (
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.serializers import StudentPracticeSerializer
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus
from users.services import get_user_department_ids

PRACTICE_TRANSITIONS = {
    PracticeWorkflowState.PENDING_CONTENT_APPROVAL: [
        PracticeWorkflowState.CONTENT_APPROVED,
        PracticeWorkflowState.CONTENT_REJECTED,
    ],
    PracticeWorkflowState.CONTENT_APPROVED: [
        PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
    ],
    PracticeWorkflowState.CONTENT_REJECTED: [
        PracticeWorkflowState.PENDING_CONTENT_APPROVAL,
    ],
    PracticeWorkflowState.OPEN_FOR_APPLICATIONS: [
        PracticeWorkflowState.CLOSED_FOR_APPLICATIONS,
    ],
}


class PracticeService:
    @staticmethod
    def encode_logo_to_base64(logo):
        if not logo or not hasattr(logo, "path"):
            return None

        try:
            mime_type, _ = mimetypes.guess_type(logo.path)
            prefix = f"data:{mime_type or 'image/png'};base64,"

            with open(logo.path, "rb") as img_file:
                return prefix + base64.b64encode(img_file.read()).decode("utf-8")
        except (OSError, ValueError):
            return None

    @staticmethod
    def get_user_practices_and_invitations(user):
        student_practices = StudentPractice.objects.filter(user=user).select_related("practice", "practice__employer")

        sp_data = [
            {
                "student_practice_id": sp.student_practice_id,
                "practice_id": sp.practice.practice_id,
                "practice_title": sp.practice.title,
                "company_logo": sp.practice.image_base64,
                "application_date": sp.application_date,
                "status": sp.approval_status,
            }
            for sp in student_practices
        ]

        invitations = EmployerInvitation.objects.filter(user=user, status=EmployerInvitationStatus.PENDING).select_related(
            "practice", "practice__employer"
        )

        inv_data = [
            {
                "invitation_id": ei.invitation_id,
                "practice_id": ei.practice.practice_id if ei.practice else None,
                "practice_title": ei.practice.title if ei.practice else None,
                "company_logo": ei.practice.image_base64 if ei.practice else None,
                "submission_date": ei.submission_date,
                "status": ei.status,
            }
            for ei in invitations
        ]

        return {
            "student_practices": sp_data,
            "employer_invitations": inv_data,
        }

    @staticmethod
    @transaction.atomic
    def apply_student_practice(user, practice_id: int) -> dict:
        """
        Create a StudentPractice record for the user and practice.
        Raises ValueError if validation fails.
        """
        from users.models import StudentUser

        # C3.5 guard: only students can apply
        if not isinstance(user, StudentUser):
            raise ValueError("ONLY_STUDENTS_CAN_APPLY")

        # C3.3: lock the practice row to prevent race conditions on capacity
        practice = Practice.objects.select_for_update().filter(practice_id=practice_id, is_active=True).first()
        if not practice:
            raise ValueError(PracticeMessages.NOT_FOUND)

        # C3.3: guard — practice must be open for applications (None = backward compat)
        if practice.workflow_state is not None and practice.workflow_state != PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
            raise ValueError("PRACTICE_NOT_OPEN_FOR_APPLICATIONS")

        if not practice.start_date or not practice.end_date:
            raise ValueError("MISSING_DATES")

        # 3.7: Blokace storna — practice byla stornována
        if practice.is_cancelled:
            raise ValueError("PRACTICE_IS_CANCELLED")

        # C3.3: capacity guard — available_positions > 0 and not already full
        if practice.available_positions is not None and practice.available_positions <= 0:
            raise ValueError("NO_CAPACITY_AVAILABLE")
        if practice.available_positions is not None:
            active_count = StudentPractice.objects.filter(
                practice_id=practice_id,
                is_cancelled=False,
                workflow_state__in=[
                    StudentPracticeWorkflowState.APPLIED,
                    StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
                    StudentPracticeWorkflowState.CONTRACTED,
                    StudentPracticeWorkflowState.STARTED,
                    StudentPracticeWorkflowState.COMPLETED,
                    StudentPracticeWorkflowState.ENDED,
                ],
            ).count()
            if active_count >= practice.available_positions:
                raise ValueError("CAPACITY_FULL")

        # 3.7: Blokace storna — pokud má student nevyřešené storno, blokovat přihlášku
        unresolved_cancellation = StudentPractice.objects.filter(
            user=user,
            is_cancelled=True,
            cancellation_resolved_at__isnull=True,
        ).exists()
        if unresolved_cancellation:
            raise ValueError("Máte nevyřešené storno")

        # C3.4: allow re-application only if previous was rejected or cancelled
        existing_active = StudentPractice.objects.filter(
            practice_id=practice_id,
            user=user,
            is_cancelled=False,
            workflow_state__in=[
                StudentPracticeWorkflowState.APPLIED,
                StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
                StudentPracticeWorkflowState.CONTRACTED,
                StudentPracticeWorkflowState.STARTED,
                StudentPracticeWorkflowState.COMPLETED,
                StudentPracticeWorkflowState.ENDED,
            ],
        ).exists()
        if existing_active:
            raise ValueError(PracticeMessages.ALREADY_APPLIED)

        data = {
            "user": user.pk,
            "practice": practice_id,
            "application_date": date.today(),
            "approval_status": ApprovalStatus.PENDING.value,
            "progress_status": ProgressStatus.NOT_STARTED.value,
            "hours_completed": 0,
            "year": date.today().year,
            "start_date": practice.start_date.strftime("%d.%m.%Y"),
            "end_date": practice.end_date.strftime("%d.%m.%Y"),
        }

        serializer = StudentPracticeSerializer(data=data)
        if serializer.is_valid():
            try:
                student_practice = serializer.save()
            except IntegrityError:
                raise ValueError(PracticeMessages.ALREADY_APPLIED)

            # C3.1: set workflow_state directly — serializer drops it (field not in Meta.fields)
            student_practice.workflow_state = StudentPracticeWorkflowState.APPLIED
            student_practice.save(update_fields=["workflow_state"])

            EmailService.notify_org_new_application(student_practice)

            if practice.contact_user:
                NotificationService.create_notification(
                    recipient=practice.contact_user,
                    verb="NEW_APPLICATION",
                    message=f"Student {user.full_name} se přihlásil na vaši nabídku praxe '{practice.title}'.",
                    actor=user,
                    target=student_practice,
                    notification_type=NotificationType.INFO,
                )

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.APPLY,
                object_type="StudentPractice",
                object_id=serializer.data.get("student_practice_id"),
                description=f"Student {user.email} se přihlásil na praxi ID {practice_id}",
            )

            return serializer.data
        else:
            error_msg = "; ".join([f"{k}: {v}" for k, v in serializer.errors.items()])
            raise ValueError(error_msg)

    @staticmethod
    def get_practices_by_department(user):
        dept_ids = get_user_department_ids(user)

        if not dept_ids:
            return None

        # Ongoing/Approved student practices (actual internships)
        approved_student_practices = StudentPractice.objects.filter(
            practice__subject__department_id__in=dept_ids,
            practice__is_cancelled=False,
            approval_status=ApprovalStatus.APPROVED,
        ).select_related(
            "user",
            "practice",
            "practice__subject",
            "practice__subject__department",
            "practice__employer",
            "practice__contact_user",
        )

        to_approve_offers = Practice.objects.filter(
            subject__department_id__in=dept_ids,
            approval_status=ApprovalStatus.PENDING,
            is_active=True,
            is_cancelled=False,
        ).select_related("subject", "subject__department", "contact_user", "employer")

        return {
            "approved": approved_student_practices,
            "to_approve": to_approve_offers,
        }

    @staticmethod
    def enrich_contact_user_info(practice_data_list, practices_queryset):
        practice_map = {p.practice_id: p for p in practices_queryset}

        for item in practice_data_list:
            practice_id = item.get("practice_id")
            if practice_id and practice_id in practice_map:
                practice = practice_map[practice_id]
                user = getattr(practice, "contact_user", None)
                if user:
                    item["contact_user_info"] = {
                        "user_id": user.user_id,
                        "username": getattr(user, "username", None),
                        "first_name": getattr(user, "first_name", None),
                        "last_name": getattr(user, "last_name", None),
                        "email": getattr(user, "email", None),
                        "phone": getattr(user, "phone", None),
                    }
                else:
                    item["contact_user_info"] = None
        return practice_data_list

    @staticmethod
    @transaction.atomic
    def transition_practice_state(practice, target_state, actor, reason=None) -> Practice:
        """
        Validates and executes a transition of the practice workflow state.

        Uses PRACTICE_TRANSITIONS to determine allowed transitions.
        Raises ValueError if the transition is not permitted or the practice is cancelled.
        """
        practice = Practice.objects.select_for_update().get(pk=practice.pk)
        if practice.is_cancelled:
            raise ValueError("STORNOVANOU_PRAXI_NELZE_MODIFIKOVAT")

        current_state = practice.workflow_state

        # If no state set yet, allow any target state EXCEPT OPEN_FOR_APPLICATIONS
        # (which is always gated by the CONTENT_APPROVED check below).
        if current_state is not None:
            allowed_targets = PRACTICE_TRANSITIONS.get(current_state, [])
            if target_state not in allowed_targets:
                raise ValueError(f"PREVOD_Z_{current_state.name}_DO_{target_state.name}_NENI_POVOLEN")

        # Special validation: OPEN_FOR_APPLICATIONS requires CONTENT_APPROVED
        if target_state == PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
            if current_state != PracticeWorkflowState.CONTENT_APPROVED:
                raise ValueError("OTEVRENI_VYHRADUJE_SCHVALENEMU_OBSAHU")
            practice.is_active = True

        # C3.6: CLOSED_FOR_APPLICATIONS must set closure metadata (was bypassed)
        if target_state == PracticeWorkflowState.CLOSED_FOR_APPLICATIONS:
            practice.closed_for_applications_at = timezone.now()
            practice.closed_reason = ApplicationClosureReason.MANUAL
            practice.is_active = False

        practice.workflow_state = target_state
        practice.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="Practice",
            object_id=practice.pk,
            description=(
                f"Prechod stavu praxe ID {practice.pk}: "
                f"{current_state.name if current_state else 'None'} -> {target_state.name}" + (f" (duvod: {reason})" if reason else "")
            ),
        )

        # --- Send in-app notification ---
        org_contact = practice.contact_user
        if org_contact:
            if target_state == PracticeWorkflowState.CONTENT_APPROVED:
                NotificationService.create_notification(
                    recipient=org_contact,
                    verb="PRACTICE_CONTENT_APPROVED",
                    message=f"Obsah vaší nabídky praxe '{practice.title}' byl schválen.",
                    actor=actor,
                    target=practice,
                    notification_type=NotificationType.SUCCESS,
                )
            elif target_state == PracticeWorkflowState.CONTENT_REJECTED:
                NotificationService.create_notification(
                    recipient=org_contact,
                    verb="PRACTICE_CONTENT_REJECTED",
                    message=f"Obsah vaší nabídky praxe '{practice.title}' byl zamítnut." + (f" Důvod: {reason}" if reason else ""),
                    actor=actor,
                    target=practice,
                    notification_type=NotificationType.ERROR,
                )
            elif target_state == PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
                NotificationService.create_notification(
                    recipient=org_contact,
                    verb="PRACTICE_OPENED",
                    message=f"Vaše nabídka praxe '{practice.title}' byla otevřena pro přihlášky studentů.",
                    actor=actor,
                    target=practice,
                    notification_type=NotificationType.SUCCESS,
                )

        return practice

    @staticmethod
    @transaction.atomic
    def cancel_practice(practice, actor, reason: str) -> Practice:
        """
        Cancels a practice by setting cancellation mixin fields and deactivating it.

        Raises ValueError if already cancelled or reason is empty.
        """
        practice = Practice.objects.select_for_update().get(pk=practice.pk)
        if practice.is_cancelled:
            raise ValueError("PRAXE_JE_JIZ_STORNOVANA")

        if not reason or not reason.strip():
            raise ValueError("DUVOD_STORNA_JE_POVINNY")

        practice.is_cancelled = True
        practice.cancelled_at = timezone.now()
        practice.cancelled_by = actor
        practice.cancellation_reason = reason.strip()
        practice.is_active = False
        practice.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STORNO,
            object_type="Practice",
            object_id=practice.pk,
            description=f"Stornovana praxe ID {practice.pk}: {reason.strip()}",
        )

        # --- Notify org contact ---
        org_contact = practice.contact_user
        if org_contact:
            NotificationService.create_notification(
                recipient=org_contact,
                verb="PRACTICE_CANCELLED",
                message=f"Vaše nabídka praxe '{practice.title}' byla zrušena. Důvod: {reason.strip()}",
                actor=actor,
                target=practice,
                notification_type=NotificationType.WARNING,
            )

        # --- Deactivate + notify affected students ---
        from student_practices.services import StudentPracticeService

        affected_sps = StudentPractice.objects.filter(
            practice=practice,
            is_cancelled=False,
        ).select_related("user")
        for sp in affected_sps:
            StudentPracticeService.cancel_student_practice(sp, actor, f"Praxe byla zrušena: {reason.strip()}")

        return practice

    @staticmethod
    @transaction.atomic
    def close_practice_for_applications(practice, reason: ApplicationClosureReason, actor) -> Practice:
        """
        Closes a practice that is currently open for applications.

        Raises ValueError if the practice is cancelled or not currently open for applications.
        """
        practice = Practice.objects.select_for_update().get(pk=practice.pk)
        if practice.is_cancelled:
            raise ValueError("STORNOVANOU_PRAXI_NELZE_MODIFIKOVAT")

        if practice.workflow_state != PracticeWorkflowState.OPEN_FOR_APPLICATIONS:
            raise ValueError("POUZE_OTEVRENY_SBER_LZE_UZAVRIT")

        practice.workflow_state = PracticeWorkflowState.CLOSED_FOR_APPLICATIONS
        practice.closed_for_applications_at = timezone.now()
        practice.closed_reason = reason
        practice.is_active = False
        practice.save()

        ActionLogService.log(
            user=actor,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="Practice",
            object_id=practice.pk,
            description=(f"Uzavreni sberu prhlas praxe ID {practice.pk}: " f"z duvodu {reason.name}"),
        )

        org_contact = practice.contact_user
        if org_contact:
            NotificationService.create_notification(
                recipient=org_contact,
                verb="APPLICATIONS_CLOSED",
                message=f"Přihlašování na vaši nabídku '{practice.title}' bylo uzavřeno.",
                actor=actor,
                target=practice,
                notification_type=NotificationType.INFO,
            )

        return practice

    @staticmethod
    def get_organization_practices_queryset(employer_profile):
        return (
            Practice.objects.filter(
                employer=employer_profile,
                is_cancelled=False,
                is_active=True,
            )
            .select_related("subject", "subject__department", "contact_user")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.APPROVED),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
            .order_by("-created_at")
        )
