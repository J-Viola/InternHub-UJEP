from datetime import date

from django.db import transaction

from practices.models import Practice, ProgressStatus
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
            raise ValueError("Praxe nenalezena.")

        # Optional: Check if user owns the practice if user is passed
        if hasattr(user, "employer_profile") and practice.employer != user.employer_profile:
            raise ValueError("Nemáte oprávnění zvát studenty na tuto praxi.")

        created_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = StudentUser.objects.get(pk=student_id)

                # Skip if student already has an active practice for this offer
                if StudentPractice.objects.filter(practice=practice, user=student).exists():
                    continue

                # Use get_or_create to avoid race condition on duplicate invitations
                _, created = EmployerInvitation.objects.get_or_create(
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
            invitation = EmployerInvitation.objects.get(invitation_id=invitation_id, user=user)
        except EmployerInvitation.DoesNotExist:
            raise ValueError("Pozvánka nebyla nalezena nebo k ní nemáte přístup.")

        if invitation.status != EmployerInvitationStatus.PENDING:
            raise ValueError("Pozvánka již byla zpracována.")

        if action == "accept":
            invitation.status = EmployerInvitationStatus.ACCEPTED
            invitation.save()

            student_practice = StudentPractice.objects.create(
                user=user,
                practice=invitation.practice,
                application_date=date.today(),
                approval_status=ApprovalStatus.APPROVED,
                progress_status=ProgressStatus.IN_PROGRESS,
                hours_completed=0,
                start_date=invitation.practice.start_date,
                end_date=invitation.practice.end_date,
                year=date.today().year,
            )

            # Explicitly generate default documents
            DocumentHelper.assign_default_documents(student_practice)

            return {
                "detail": "Pozvánka byla přijata a praxe byla zahájena.",
                "student_practice_id": student_practice.student_practice_id,
            }

        elif action == "reject":
            invitation.status = EmployerInvitationStatus.REJECTED
            invitation.save()
            return {"detail": "Pozvánka byla zamítnuta."}

        raise ValueError("Neplatná akce.")
