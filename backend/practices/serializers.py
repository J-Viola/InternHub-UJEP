from datetime import date

from api.models import ApprovalStatus, EmployerProfile, Practice, ProgressStatus, StudentPractice
from api.serializers import FormattedDateField
from rest_framework import serializers


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
            "semester",
        ]

    def get_user_info(self, obj):
        if obj.user:
            return {"user_id": obj.user.user_id, "full_name": obj.user.full_name, "email": obj.user.email}
        return None


class RunningPracticeSerializer(serializers.ModelSerializer):
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployerProfile.objects.all(), source="employer", write_only=True, required=True
    )
    subject_code = serializers.CharField(source="subject.subject_code", read_only=True)
    contact_user_name = serializers.CharField(source="contact_user.full_name", read_only=True)
    # Add student practice related fields
    student_count = serializers.SerializerMethodField()
    approved_student_count = serializers.SerializerMethodField()
    pending_student_count = serializers.SerializerMethodField()
    completed_student_count = serializers.SerializerMethodField()
    start_date = FormattedDateField()
    end_date = FormattedDateField()

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "employer_id",
            "subject_code",
            "title",
            "start_date",
            "end_date",
            "contact_user_name",
            "student_count",
            "approved_student_count",
            "pending_student_count",
            "completed_student_count",
            "available_positions",
        ]
        read_only_fields = ["practice_id", "is_active"]

    def get_contact_user_info(self, obj):
        if obj.contact_user:
            return {
                "user_id": obj.contact_user.user_id,
                "username": obj.contact_user.username,
                "email": obj.contact_user.email,
                "full_name": obj.contact_user.full_name,
            }
        return None

    def get_student_count(self, obj):
        return obj.student_practices.count()

    def get_approved_student_count(self, obj):
        return obj.student_practices.filter(approval_status=ApprovalStatus.APPROVED).count()

    def get_pending_student_count(self, obj):
        return obj.student_practices.filter(approval_status=ApprovalStatus.PENDING).count()

    def get_completed_student_count(self, obj):
        return obj.student_practices.filter(progress_status=ProgressStatus.COMPLETED).count()

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("Datum ukončení nemůže být před datem zahájení.")
        if start and start < date.today():
            raise serializers.ValidationError("Datum zahájení nemůže být v minulosti.")
        return data

    def create(self, validated_data):
        if "is_active" not in validated_data:
            validated_data["is_active"] = True
        if "progress_status" not in validated_data:
            validated_data["progress_status"] = ProgressStatus.NOT_STARTED
        if "approval_status" not in validated_data:
            validated_data["approval_status"] = ApprovalStatus.PENDING
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PracticeApprovalSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    department_name = serializers.CharField(source='subject.department.department_name', read_only=True)
    contact_user_full_name = serializers.CharField(source='contact_user.full_name', read_only=True)
    contact_user_email = serializers.CharField(source='contact_user.email', read_only=True)
    created_at = FormattedDateField(source='created_at', read_only=True)
    class Meta:
        model = Practice
        fields = [
            'practice_id', 'title', 'created_at',
            'subject_name', 'subject_code',
            'department_name',
            'contact_user_id', 'contact_user_email',
            'contact_user_full_name'
        ]