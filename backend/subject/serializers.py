from api.models import Department, ProfessorUser, Subject, UserSubject, UserSubjectType
from rest_framework import serializers


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["department_id", "department_name"]


class SubjectSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["subject_id", "subject_code", "subject_name", "department", "hours_required", "teacher"]

    def get_teacher(self, obj):
        teacher_relationship = UserSubject.objects.filter(subject=obj, role=UserSubjectType.Professor).select_related("user").first()

        if teacher_relationship:
            return TeacherSerializer(teacher_relationship.user).data
        return None


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessorUser
        fields = ["user_id", "full_name", "email"]
