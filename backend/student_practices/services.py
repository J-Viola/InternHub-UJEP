from datetime import date

from api.models import (
    ApprovalStatus,
    EmployerInvitation,
    EmployerInvitationStatus,
    ProgressStatus,
    StudentPractice,
)
from django.db import transaction


class StudentPracticeService:
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
