from api.models import Department, Practice, ProfessorUser, StudentPractice, StudentUser, UserSubjectType
from django.core.handlers.base import logger
from rest_framework import serializers


class StudentThisPracticeSerializer(serializers.ModelSerializer):
    practice = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), write_only=True, required=True)

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "practice",
            "approval_status",
            "progress_status",
        ]
        read_only_fields = [
            "student_practice_id",
            "practice",
            "approval_status",
            "progress_status",
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="first_name")
    surname = serializers.CharField(source="last_name")
    student_practice = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    approved_practice = serializers.SerializerMethodField()

    class Meta:
        model = StudentUser
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "name",
            "surname",
            "email",
            "os_cislo",
            "student_practice",
            "department",
            "approved_practice",
        )

    def get_student_practice(self, obj):
        qs = list(obj.student_practices.all())
        count = len(qs)
        if count > 1:
            logger.warning(f"User {obj.user_id} has {count} practices; only the first will be shown")
        first = qs[0] if qs else None
        return StudentThisPracticeSerializer(first).data if first else None

    def get_department(self, obj):
        qs = obj.user_subjects.filter(role=UserSubjectType.Student)
        dept_names = qs.values_list("subject__department__department_name", flat=True).distinct()
        return dept_names[0] if dept_names else None

    def get_approved_practice(self, obj):
        approved = obj.student_practices.filter(approval_status=1).first()
        if approved:
            return {
                "student_practice_id": approved.student_practice_id,
                "approval_status": approved.approval_status,
            }
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentUser
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


class ProfessorSubjectSerializer(serializers.Serializer):
    subject_name = serializers.CharField(source="subject.subject_name")
    subject_id = serializers.CharField(source="subject.subject_id")


class ProfessorDetailSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = StudentUser
        fields = ("user_id", "first_name", "last_name", "email", "department", "subjects")

    def get_subjects(self, obj):
        professor_subjects = obj.user_subjects.filter(role=UserSubjectType.Professor)
        return ProfessorSubjectSerializer(professor_subjects, many=True).data

    def get_department(self, obj):
        qs = obj.user_subjects.filter(role=UserSubjectType.Professor)
        dept_name = qs.values_list("subject__department__department_name", flat=True).distinct().first()
        return dept_name if dept_name else None


class DepartmentUserSerializer(serializers.Serializer):
    user_type = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    def get_user_type(self, obj):
        if isinstance(obj, StudentUser):
            return "student"
        elif isinstance(obj, ProfessorUser):
            return "professor"
        return "unknown"

    def get_data(self, obj):
        if isinstance(obj, StudentUser):
            return StudentDetailSerializer(obj).data
        elif isinstance(obj, ProfessorUser):
            return ProfessorDetailSerializer(obj).data
        return {}

    class Meta:
        fields = ("user_type", "data")


class AdminDepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = "__all__"
