from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "actor",
            "actor_name",
            "verb",
            "message",
            "notification_type",
            "is_read",
            "created_at",
            "content_type",
            "object_id",
        ]
        read_only_fields = ["id", "created_at"]

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else ""
