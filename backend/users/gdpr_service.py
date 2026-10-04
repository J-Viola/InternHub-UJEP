import logging
from datetime import datetime

from django.db import transaction

from users.action_log import ActionLogService
from users.constants import ActionLogType

logger = logging.getLogger(__name__)


class GDPRService:
    @staticmethod
    @transaction.atomic
    def anonymize_user(user):
        """
        Anonymizes PII data of a user per GDPR Article 17 (Right to Erasure).
        Deactivates account and logs ActionLog.
        """
        user_id = user.user_id

        # Anonymize PII
        user.first_name = "Anonymized"
        user.last_name = f"User_{user_id}"
        user.email = f"anonymized_{user_id}@anonymized.local"
        user.is_active = False

        if hasattr(user, "phone"):
            user.phone = ""
        if hasattr(user, "cv_file") and user.cv_file:
            user.cv_file.delete(save=False)
            user.cv_file = None

        # StudentUser-specific PII fields
        from users.models import StudentUser

        if isinstance(user, StudentUser):
            user.date_of_birth = None
            user.place_of_birth = ""
            user.street = ""
            user.street_number = ""
            user.zip_code = ""
            user.city = ""
            user.skills = []
            if user.profile_picture:
                user.profile_picture.delete(save=False)
                user.profile_picture = None
            user.resume = ""
            user.additional_info = ""

        # EmployerProfile PII fields
        if hasattr(user, "employer_profile") and user.employer_profile:
            user.employer_profile.address = ""
            user.employer_profile.zip_code = ""
            user.employer_profile.save()

        user.save()

        ActionLogService.log(
            user=None,
            action_type=ActionLogType.DELETE,
            object_type="User",
            object_id=user_id,
            description=f"GDPR Anonymizace uživatele ID {user_id}",
        )
        return user

    @staticmethod
    def export_user_data(user) -> dict:
        """
        Exports all personal data of a user per GDPR Article 20 (Right to Data Portability).
        """
        data = {
            "export_date": datetime.now().isoformat(),
            "user_info": {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined.isoformat() if hasattr(user, "date_joined") and user.date_joined else None,
            },
            "consents": [],
            "practices": [],
            "applications": [],
        }

        # Consents
        if hasattr(user, "consents"):
            data["consents"] = [
                {
                    "type": c.consent_type,
                    "agreed": c.agreed,
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in user.consents.all()
            ]

        # Student practices
        if hasattr(user, "student_practices"):
            data["applications"] = [
                {
                    "practice_id": sp.practice_id,
                    "practice_title": sp.practice.title if sp.practice else "",
                    "application_date": str(sp.application_date),
                    "workflow_state": sp.workflow_state,
                    "approval_status": str(sp.approval_status),
                }
                for sp in user.student_practices.all()
            ]

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.VIEW,
            object_type="User",
            object_id=user.user_id,
            description=f"GDPR Export dat uživatele ID {user.user_id}",
        )
        return data
