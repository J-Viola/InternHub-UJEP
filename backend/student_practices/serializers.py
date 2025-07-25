from api.helpers import FormattedDateField
from api.models import Practice, StudentPractice, EmployerInvitation
from rest_framework import serializers


class EmployerInvitationApprovalSerializer(serializers.Serializer):
    invitation_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['accept', 'reject'])


class StudentPracticeSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "user",
            "user_info",
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
            "cancellation_reason",
            "year",
        ]

    def get_user_info(self, obj):
        if obj.user:
            return {"user_id": obj.user.user_id, "full_name": obj.user.full_name, "email": obj.user.email}
        return None


class ListStudentPracticeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model StudentPractice
    - student_practice_id: primární klíč (read-only)
    - practice_id: PK praxe (read-only)
    - practice_title: název praxe (read-only)
    - application_date: datum podání žádosti (read-only)
    - approval_status: nested Status (read-only)
    - progress_status: nested Status (read-only)
    - hours_completed: počet dokončených hodin
    """

    practice_id = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), required=True)
    practice_title = serializers.CharField(source="practice.title", read_only=True)
    department_name = serializers.CharField(source="practice.subject.department.department_name", read_only=True)
    application_date = FormattedDateField(read_only=True)
    student_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_id = serializers.IntegerField(source="user.user_id", read_only=True)

    class Meta:
        model = StudentPractice
        fields = [
            "practice_id",
            "student_practice_id",
            "department_name",
            "student_full_name",
            "user_id",
            "practice_title",
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
        ]
        read_only_fields = [
            "student_practice_id",
            "practice_title",
            "application_date",
        ]


class StudentPracticeStatusSerializer(serializers.ModelSerializer):
    application_date = FormattedDateField(read_only=True, allow_null=True)

    class Meta:
        model = StudentPractice
        fields = [
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
        ]
