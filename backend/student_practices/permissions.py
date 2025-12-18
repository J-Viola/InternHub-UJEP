from rest_framework import permissions

from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubjectType,
)


class IsSubjectTeacherOrHeadForPractice(permissions.BasePermission):
    """
    Umožní přístup, pokud je uživatel učitel (ProfessorUser) a:
    1. Je vedoucím katedry (HEAD) pod kterou spadá předmět praxe.
    2. Je garantem (subject_manager) předmětu praxe.
    3. Je vyučujícím předmětu praxe (přes UserSubject).
    """

    def has_object_permission(self, request, view, obj):
        # obj is StudentPractice instance
        if not isinstance(request.user, ProfessorUser):
            return False

        practice_subject = obj.practice.subject
        if not practice_subject:
            return False

        # 1. Vedoucí katedry
        if request.user.department_role == DepartmentRole.HEAD and request.user.department == practice_subject.department:
            return True

        # 2. Garant předmětu
        if practice_subject.subject_manager == request.user:
            return True

        # 3. Vyučující předmětu
        if request.user.user_subjects.filter(subject=practice_subject, role=UserSubjectType.Professor).exists():
            return True

        return False


class IsPracticeOrganizationOwner(permissions.BasePermission):
    """
    Umožní přístup, pokud je uživatel členem organizace, která vypsala danou praxi.
    """

    def has_object_permission(self, request, view, obj):
        # obj is StudentPractice
        return hasattr(request.user, "employer_profile") and obj.practice.employer == request.user.employer_profile


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
