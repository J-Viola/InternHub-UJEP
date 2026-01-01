from datetime import date

from django.db import transaction

from practices.models import Practice, ProgressStatus
from student_practices.messages import StudentPracticeMessages
from student_practices.models import (
    DocumentHelper,
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
)
from users.models import ApprovalStatus, StudentUser


class StudentPracticeService:
    @staticmethod
    @transaction.atomic
    def create_invitations(user, practice_id: int, student_ids: list[int]) -> dict:
        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            raise ValueError(StudentPracticeMessages.PRACTICE_NOT_FOUND)

        # Optional: Check if user owns the practice if user is passed
        if (
            hasattr(user, "employer_profile")
            and practice.employer != user.employer_profile
        ):
            raise ValueError(StudentPracticeMessages.UNAUTHORIZED)

        created_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = StudentUser.objects.get(pk=student_id)

                # Skip if student already has an active practice for this offer
                if StudentPractice.objects.filter(
                    practice=practice, user=student
                ).exists():
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
                    created_count += 1
            except StudentUser.DoesNotExist:
                errors.append(f"Student ID {student_id} neexistuje.")

        return {"created": created_count, "errors": errors}

    @staticmethod
    @transaction.atomic
    def process_invitation_approval(user, invitation_id, action):
        """
        Process the approval or rejection of an employer invitation.
        """
        try:
            invitation = EmployerInvitation.objects.get(
                invitation_id=invitation_id, user=user
            )
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

            return {
                "detail": StudentPracticeMessages.INVITATION_ACCEPTED,
                "student_practice_id": student_practice.student_practice_id,
            }

        elif action == "reject":
            invitation.status = EmployerInvitationStatus.REJECTED
            invitation.save()
            return {"detail": StudentPracticeMessages.INVITATION_REJECTED}

        raise ValueError(StudentPracticeMessages.INVALID_ACTION)

    @staticmethod
    @transaction.atomic
    def update_student_practice_status(user, student_practice_id: int, data: dict):
        """
        Updates the status of a StudentPractice with transaction safety (select_for_update)
        to handle dual approval correctly.
        """
        from users.models import (
            DepartmentRole,
            OrganizationUser,
            ProfessorUser,
            UserSubjectType,
        )

        # Use select_for_update to lock the row
        try:
            student_practice = StudentPractice.objects.select_for_update().get(
                pk=student_practice_id
            )
        except StudentPractice.DoesNotExist:
            raise ValueError(StudentPracticeMessages.NOT_FOUND)

        # Determine roles for the user relative to this specific practice
        is_professor = isinstance(user, ProfessorUser)
        is_org = isinstance(user, OrganizationUser)
        is_admin = user.is_superuser

        # Detailed role check for professor (must be from same dept or teacher of the subject)
        if is_professor and not is_admin:
            subject = student_practice.practice.subject
            is_head = (
                user.department_role == DepartmentRole.HEAD
                and user.department == subject.department
            )
            is_manager = subject.subject_manager == user
            is_teacher = user.user_subjects.filter(
                subject=subject, role=UserSubjectType.Professor
            ).exists()
            if not (is_head or is_manager or is_teacher):
                is_professor = False  # Not authorized for THIS practice

        # Detailed role check for org (must be from the same organization)
        if is_org and not is_admin:
            if student_practice.practice.employer != getattr(
                user, "employer_profile", None
            ):
                is_org = False  # Not authorized for THIS practice

        # GLOBAL AUTHORIZATION CHECK
        if not (is_professor or is_org or is_admin):
            raise ValueError(StudentPracticeMessages.UNAUTHORIZED)

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
                if (
                    student_practice.school_approved
                    and student_practice.employer_approved
                ):
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
            if (
                student_practice.approval_status != ApprovalStatus.APPROVED
                and not is_admin
            ):
                raise ValueError(StudentPracticeMessages.PROGRESS_UPDATE_FORBIDDEN)

            try:
                student_practice.progress_status = int(data["progress_status"])
            except (ValueError, TypeError):
                raise ValueError(StudentPracticeMessages.INVALID_PROGRESS_VALUE)

        # 3. Handle other fields (hours_completed, notes, etc.)
        if "hours_completed" in data:
            student_practice.hours_completed = data["hours_completed"]

        student_practice.save()
        return student_practice

    @staticmethod
    @transaction.atomic
    def process_document_review(
        user, document_id: int, status_val: int, review_note: str = ""
    ):
        """
        Allows a professor or admin to approve or reject a document.
        """
        from student_practices.models import UploadedDocument
        from users.models import (
            DepartmentRole,
            ProfessorUser,
            UserSubjectType,
        )

        document = UploadedDocument.objects.select_for_update().get(pk=document_id)
        student_practice = document.student_practice

        if not student_practice:
            raise ValueError(StudentPracticeMessages.NOT_FOUND)

        is_professor = isinstance(user, ProfessorUser)
        is_admin = user.is_superuser

        if is_professor and not is_admin:
            subject = student_practice.practice.subject
            is_head = (
                user.department_role == DepartmentRole.HEAD
                and user.department == subject.department
            )
            is_manager = subject.subject_manager == user
            is_teacher = user.user_subjects.filter(
                subject=subject, role=UserSubjectType.Professor
            ).exists()
            if not (is_head or is_manager or is_teacher):
                raise ValueError(StudentPracticeMessages.UNAUTHORIZED)

        if not (is_professor or is_admin):
            raise ValueError(StudentPracticeMessages.UNAUTHORIZED)

        document.status = status_val
        document.review_note = review_note
        document.save()

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
        from student_practices.models import DocumentStatus

        if (
            student_practice.approval_status == ApprovalStatus.APPROVED
            and student_practice.progress_status == ProgressStatus.NOT_STARTED
        ):
            # Check mandatory documents
            contract_ok = (
                student_practice.contract_document
                and student_practice.contract_document.status == DocumentStatus.APPROVED
            )
            content_ok = (
                student_practice.content_document
                and student_practice.content_document.status == DocumentStatus.APPROVED
            )

            if contract_ok and content_ok:
                student_practice.progress_status = ProgressStatus.IN_PROGRESS
                student_practice.save()
