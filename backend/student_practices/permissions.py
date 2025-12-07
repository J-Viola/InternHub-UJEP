from rest_framework import permissions

from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubjectType,
)


class HasDocumentAccess(permissions.BasePermission):
    """
    Custom permission to check if user has access to the document.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        # obj is UploadedDocument instance

        if user.is_superuser:
            return True

        if isinstance(user, StudentUser):
            return obj.student_practice.user == user

        elif isinstance(user, ProfessorUser):
            # Check if professor is assigned to the subject
            user_subjects = obj.student_practice.practice.subject.user_subjects
            is_professor_for_subject = user_subjects.filter(user=user, role=UserSubjectType.Professor).exists()
            if is_professor_for_subject:
                return True

            # Check if professor is head of the department
            if user.department_role == DepartmentRole.HEAD and user.department == obj.student_practice.practice.subject.department:
                return True

        elif isinstance(user, OrganizationUser):
            # Organizační uživatel má přístup k dokumentům praxí své organizace
            return obj.student_practice.practice.employer == user.employer_profile

        return False
