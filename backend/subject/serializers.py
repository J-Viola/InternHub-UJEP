from api.models import Department, StagUser, Subject, UserSubject, UserSubjectType
from rest_framework import serializers


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["department_id", "department_name"]


class SubjectSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source="department", read_only=True)
    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["subject_id", "subject_code", "subject_name", "department", "department_details", "hours_required", "teacher"]

    def get_teacher(self, obj):
        # Get the primary teacher for this subject (assuming first one found)
        teacher_relationship = UserSubject.objects.filter(subject=obj, role=UserSubjectType.Teacher).select_related("user").first()

        if teacher_relationship:
            return TeacherSerializer(teacher_relationship.user).data
        return None


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = StagUser
        fields = ["user_id", "title_before", "first_name", "last_name", "title_after", "email"]
