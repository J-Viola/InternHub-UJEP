from api.models import Department, ProfessorUser, Subject, UserSubject, UserSubjectType
from department.serializers import DepartmentSerializer
from rest_framework import serializers


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessorUser
        fields = ["user_id", "full_name", "email"]


class SubjectSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department",
        write_only=True,
        required=False,
        allow_null=True,
    )
    teacher = serializers.SerializerMethodField()
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=ProfessorUser.objects.all(),
        source="subject_manager",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Subject
        fields = [
            "subject_id",
            "subject_code",
            "subject_name",
            "department",
            "department_id",
            "hours_required",
            "teacher",
            "teacher_id",
        ]
        read_only_fields = ["subject_id"]

    def get_teacher(self, obj):
        # First check if there's a subject_manager assigned
        if obj.subject_manager:
            return TeacherSerializer(obj.subject_manager).data

        # Fallback to UserSubject relationship for backward compatibility
        teacher_relationship = UserSubject.objects.filter(subject=obj, role=UserSubjectType.Professor).select_related("user").first()

        if teacher_relationship:
            return TeacherSerializer(teacher_relationship.user).data
        return None

    def validate_subject_code(self, value):
        if Subject.objects.filter(subject_code=value).exists():
            # If updating, exclude self
            if self.instance and self.instance.subject_code == value:
                return value
            raise serializers.ValidationError("Předmět s tímto kódem již existuje.")
        return value

    def create(self, validated_data):
        """Create subject and optionally create UserSubject relationship"""
        if "hours_required" not in validated_data:
            validated_data["hours_required"] = 0

        subject = super().create(validated_data)

        # If a subject_manager was assigned, also create UserSubject relationship
        if subject.subject_manager:
            UserSubject.objects.get_or_create(
                user=subject.subject_manager,
                subject=subject,
                defaults={"role": UserSubjectType.Professor},
            )

        return subject

    def update(self, instance, validated_data):
        """Update subject and manage UserSubject relationship"""
        old_manager = instance.subject_manager
        subject = super().update(instance, validated_data)
        new_manager = subject.subject_manager

        # If manager changed, update UserSubject relationships
        if old_manager != new_manager:
            # Remove old manager's UserSubject if exists
            if old_manager:
                UserSubject.objects.filter(user=old_manager, subject=subject, role=UserSubjectType.Professor).delete()

            # Add new manager's UserSubject if exists
            if new_manager:
                UserSubject.objects.get_or_create(
                    user=new_manager,
                    subject=subject,
                    defaults={"role": UserSubjectType.Professor},
                )

        return subject
