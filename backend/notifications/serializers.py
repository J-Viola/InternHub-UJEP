from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "actor",
            "actor_name",
            "verb",
            "message",
            "url",
            "target_url",
            "notification_type",
            "is_read",
            "created_at",
            "content_type",
            "object_id",
        ]
        read_only_fields = ["id", "created_at"]

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else ""

    def get_target_url(self, obj):
        """
        Navigační URL cílového objektu (target).

        Priorita: model targetu může definovat ``get_absolute_url()``; jinak
        (zatím) None — notifikace s explicitním odkazem (např. EXPORT_READY)
        používají pole ``url``.
        """
        target = obj.target
        if target is None:
            return None
        get_absolute_url = getattr(target, "get_absolute_url", None)
        if callable(get_absolute_url):
            try:
                absolute_url = get_absolute_url()
            except Exception:
                absolute_url = None
            if absolute_url:
                return absolute_url
        return None
