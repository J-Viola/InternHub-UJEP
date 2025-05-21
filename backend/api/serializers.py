from rest_framework import serializers
from .models import (
    Status, User, ActionLog, Department, DepartmentUserRole, Subject,
    EmployerProfile, EmployerInvitation, EmployerUserRole, PracticeType,
    Practice, PracticeUser, Role, StudentPractice, UploadedDocument, UserSubject
)

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = '__all__'
        read_only_fields = ['status_id']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['user_id']

class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = '__all__'
        read_only_fields = ['action_id']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['department_id']

class DepartmentUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentUserRole
        fields = '__all__'
        read_only_fields = ['id']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
        read_only_fields = ['subject_id']

class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = '__all__'
        read_only_fields = ['employer_id']

class EmployerInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerInvitation
        fields = '__all__'
        read_only_fields = ['invitation_id']

class EmployerUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerUserRole
        fields = '__all__'
        read_only_fields = ['id']

class PracticeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeType
        fields = '__all__'
        read_only_fields = ['practice_type_id']

class PracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practice
        fields = '__all__'
        read_only_fields = ['practice_id']

class PracticeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeUser
        fields = '__all__'
        read_only_fields = ['id']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'
        read_only_fields = ['role_id']

class StudentPracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPractice
        fields = '__all__'
        read_only_fields = ['student_practice_id']

class UploadedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = '__all__'
        read_only_fields = ['document_id']

class UserSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubject
        fields = '__all__'
        read_only_fields = ['id']
