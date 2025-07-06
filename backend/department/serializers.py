from api.models import Department, Practice, StagUser, Status, StudentPractice, UserSubjectType
from api.serializers import StatusSerializer
from django.core.handlers.base import logger
from rest_framework import serializers


class StudentThisPracticeSerializer(serializers.ModelSerializer):
    practice = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), write_only=True, required=True)
    approval_status = StatusSerializer(read_only=True)
    approval_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="approval_status", write_only=True, required=False
    )

    progress_status = StatusSerializer(read_only=True)
    progress_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="progress_status", write_only=True, required=False
    )

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "practice",
            "approval_status",
            "approval_status_id",
            "progress_status",
            "progress_status_id",
        ]
        read_only_fields = [
            "student_practice_id",
            "practice",
            "approval_status",
            "approval_status_id",
            "progress_status",
            "progress_status_id",
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    student_practice_id = serializers.SerializerMethodField()
    practice = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = StagUser
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "os_cislo",
            "year_of_study",
            "field_of_study",
            "student_practice_id",
            "practice",
            "department",
        )

    def get_student_practice_id(self, obj):
        first = obj.studentpractice_set.first()
        return first.student_practice_id if first else None

    def get_practice(self, obj):
        qs = list(obj.studentpractice_set.all())
        count = len(qs)
        if count > 1:
            logger.warning(f"User {obj.user_id} has {count} practices; only the first will be shown")
        first = qs[0] if qs else None
        return StudentThisPracticeSerializer(first).data if first else None

    def get_department(self, obj):
        qs = obj.usersubject_set.filter(role=UserSubjectType.Student)
        dept_names = qs.values_list("subject__department__department_name", flat=True).distinct()
        return dept_names[0] if dept_names else None


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StagUser
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "os_cislo",
            "year_of_study",
        )


class DepartmentSerializer(serializers.ModelSerializer):
    user = StudentDetailSerializer(read_only=True)
    department = serializers.StringRelatedField()
    role = serializers.StringRelatedField()

    class Meta:
        model = Department
        fields = "__all__"
