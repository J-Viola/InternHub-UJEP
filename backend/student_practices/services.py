from datetime import date

from django.db import transaction

from practices.models import Practice, ProgressStatus
from student_practices.models import (
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

                # Check for existing invitation or practice
                if EmployerInvitation.objects.filter(practice=practice, user=student).exists():
                    continue
                if StudentPractice.objects.filter(practice=practice, user=student).exists():
                    continue

                EmployerInvitation.objects.create(
                    employer=practice.employer,
                    user=student,
                    practice=practice,
                    status=EmployerInvitationStatus.PENDING,
                    submission_date=date.today(),
                )
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
            return {
                "detail": "Pozvánka byla přijata a praxe byla zahájena.",
                "student_practice_id": student_practice.student_practice_id,
            }

        elif action == "reject":
            invitation.status = EmployerInvitationStatus.REJECTED
            invitation.save()
            return {"detail": "Pozvánka byla zamítnuta."}

        raise ValueError("Neplatná akce.")
