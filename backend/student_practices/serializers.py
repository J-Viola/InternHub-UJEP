from api.helpers import FormattedDateField
from api.models import Practice, StudentPractice
from rest_framework import serializers


class EmployerInvitationApprovalSerializer(serializers.Serializer):
    invitation_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["accept", "reject"])


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

    class Meta:
        model = StudentPractice
        fields = [
            "practice_id",
            "student_practice_id",
            "department_name",
            "student_full_name",
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


class StudentPracticeCardSerializer(serializers.ModelSerializer):
    employer = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    contact_user_info = serializers.SerializerMethodField()
    practice_type = serializers.SerializerMethodField()
    student_practice_status = serializers.SerializerMethodField()

    class Meta:
        model = Practice
        fields = [
            "employer",
            "subject",
            "title",
            "description",
            "responsibilities",
            "available_positions",
            "start_date",
            "end_date",
            "progress_status",
            "approval_status",
            "contact_user_info",
            "is_active",
            "image_base64",
            "practice_type",
            "student_practice_status",
        ]
        read_only_fields = ["practice_id", "is_active"]

    def get_contact_user_info(self, obj):
        if obj.practice.contact_user:
            return {
                "user_id": obj.practice.contact_user.user_id,
                "username": obj.practice.contact_user.username,
            }
        return None

    def get_student_practice_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        # Check if the user is a StudentUser
        if hasattr(request.user, "studentuser"):
            try:
                student_practice = StudentPractice.objects.get(user=request.user.studentuser, practice=obj)
                return StudentPracticeStatusSerializer(student_practice).data
            except StudentPractice.DoesNotExist:
                pass

        return None

    def get_employer(self, obj):
        from api.serializers import EmployerProfileSerializer

        return EmployerProfileSerializer(obj.practice.employer).data

    def get_subject(self, obj):
        from api.serializers import SubjectSerializer

        return SubjectSerializer(obj.practice.subject).data

    def get_practice_type(self, obj):
        from api.serializers import PracticeTypeSerializer

        return PracticeTypeSerializer(obj.practice.practice_type).data
