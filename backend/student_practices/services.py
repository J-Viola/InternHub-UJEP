from datetime import date

from django.db import transaction
from notifications.services import EmailService
from rest_framework.exceptions import PermissionDenied

from api.helpers import can_manage_practice
from practices.models import Practice, ProgressStatus
from student_practices.messages import StudentPracticeMessages
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
)
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus, StudentUser


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
                if StudentPractice.objects.filter(practice=practice, user=student).exists():
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

            student_practice = StudentPractice.objects.create(
                user=user,
                practice=invitation.practice,
                application_date=date.today(),
                approval_status=ApprovalStatus.PENDING,  # Still pending school's approval
                progress_status=ProgressStatus.NOT_STARTED,
                hours_completed=0,
                start_date=invitation.practice.start_date,
                end_date=invitation.practice.end_date,
                year=date.today().year,
                employer_approved=True,
                school_approved=False,
            )

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
    def update_student_practice_status(user, student_practice_id: int, data: dict):
        """
        Updates the status of a StudentPractice with transaction safety (select_for_update)
        to handle dual approval correctly.
        """
        try:
            student_practice = StudentPractice.objects.select_for_update().get(pk=student_practice_id)
        except StudentPractice.DoesNotExist:
            raise ValueError(StudentPracticeMessages.NOT_FOUND)

        old_status = student_practice.approval_status

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

        # 2. Handle progress_status update (only after full approval)
        if "progress_status" in data:
            if student_practice.approval_status != ApprovalStatus.APPROVED and not is_admin:
                raise ValueError(StudentPracticeMessages.PROGRESS_UPDATE_FORBIDDEN)

            try:
                student_practice.progress_status = int(data["progress_status"])
            except (ValueError, TypeError):
                raise ValueError(StudentPracticeMessages.INVALID_PROGRESS_VALUE)

        # 3. Handle other fields (hours_completed, notes, etc.)
        if "hours_completed" in data:
            student_practice.hours_completed = data["hours_completed"]

        student_practice.save()

        if student_practice.approval_status != old_status:
            EmailService.notify_student_application_status(student_practice)

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.STATUS_CHANGE,
            object_type="StudentPractice",
            object_id=student_practice.student_practice_id,
            description=f"Změna stavu přihlášky ID {student_practice.student_practice_id} uživatelem {user.email} (data: {data})",
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

        document.status = status_val
        document.review_note = review_note
        document.save()

        EmailService.notify_student_document_review(document)

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
                student_practice.save()

                ActionLogService.log(
                    user=None,
                    action_type=ActionLogType.STATUS_CHANGE,
                    object_type="StudentPractice",
                    object_id=student_practice.student_practice_id,
                    description=f"Praxe automaticky spuštěna (ID: {student_practice.student_practice_id})",
                )
