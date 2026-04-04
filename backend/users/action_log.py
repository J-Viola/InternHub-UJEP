from django.utils import timezone

from users.models import ActionLog


class ActionLogService:
    @staticmethod
    def log(user, action_type, object_type, object_id=None, description=""):
        try:
            ActionLog.objects.create(
                user=user,
                action_type=action_type,
                object_type=object_type,
                object_id=object_id,
                action_description=description,
                action_date=timezone.now(),
            )
        except Exception:
            pass
