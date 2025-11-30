import base64
import mimetypes
from datetime import date

from api.models import (
    ApprovalStatus,
    EmployerInvitation,
    EmployerInvitationStatus,
    Practice,
    ProgressStatus,
    StudentPractice,
)
from django.db import transaction
from django.db.models import Count, Q
from student_practices.serializers import StudentPracticeSerializer
from users.services import get_user_department_ids


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
        except Exception:
            return None

    @staticmethod
    def get_user_practices_and_invitations(user):
        student_practices = StudentPractice.objects.filter(user=user).select_related(
            "practice", "practice__employer"
        )

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

        invitations = EmployerInvitation.objects.filter(
            user=user, status=EmployerInvitationStatus.PENDING
        ).select_related("practice", "practice__employer")

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
    def apply_student_practice(user, practice_id):
        if StudentPractice.objects.filter(practice_id=practice_id, user=user).exists():
            raise ValueError("Již jste přihlášen(a) na tuto praxi.")

        practice = Practice.objects.filter(
            practice_id=practice_id, is_active=True
        ).first()
        if not practice:
            raise ValueError("Praxe nenalezena nebo není aktivní.")

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
            student_practice = serializer.save()
            return serializer.data
        else:
            error_msg = "; ".join([f"{k}: {v}" for k, v in serializer.errors.items()])
            raise ValueError(error_msg)

    @staticmethod
    def get_practices_by_department(user):
        dept_ids = get_user_department_ids(user)

        if not dept_ids:
            return None

        practices = Practice.objects.filter(
            subject__department_id__in=dept_ids, is_active=True
        )

        approved = practices.filter(approval_status=ApprovalStatus.APPROVED)
        to_approve = practices.filter(approval_status=ApprovalStatus.PENDING)

        return {
            "approved": approved,
            "to_approve": to_approve,
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
    def get_organization_practices_queryset(employer_profile):
        return (
            Practice.objects.filter(employer=employer_profile)
            .select_related("subject", "subject__department", "contact_user")
            .prefetch_related("student_practices")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(
                        student_practices__approval_status=ApprovalStatus.APPROVED
                    ),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
            .order_by("-created_at")
        )
