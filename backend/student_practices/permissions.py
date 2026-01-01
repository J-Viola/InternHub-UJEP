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
    Umožní přístup, pokud je uživatel oprávněn schválit danou praxi (Učitel/Vedoucí).
    """

    def has_object_permission(self, request, view, obj):
        from .utils import can_approve_practice

        return can_approve_practice(request.user, obj)


class IsPracticeOrganizationOwner(permissions.BasePermission):
    """
    Umožní přístup, pokud je uživatel oprávněn schválit danou praxi (Zástupce organizace).
    """

    def has_object_permission(self, request, view, obj):
        from .utils import can_approve_practice

        return can_approve_practice(request.user, obj)


class HasDocumentAccess(permissions.BasePermission):
    """
    Umožní přístup k dokumentu pouze:
    - Majiteli dokumentu (StudentUser)
    - Profesorovi, který učí daný předmět (Subject Teacher) nebo je vedoucím katedry
    - Zástupci organizace, která praxi vypsala
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        # obj is UploadedDocument instance
        sp = getattr(obj, "student_practice", None)
        if not sp:
            return False

        if isinstance(user, StudentUser):
            return sp.user == user

        elif isinstance(user, ProfessorUser):
            # Check if professor is assigned to the subject
            if not sp.practice or not sp.practice.subject:
                return False

            subject = sp.practice.subject
            user_subjects = subject.user_subjects
            is_professor_for_subject = user_subjects.filter(
                user=user, role=UserSubjectType.Professor
            ).exists()
            if is_professor_for_subject:
                return True

            # Check if professor is head of the department
            if (
                user.department_role == DepartmentRole.HEAD
                and user.department == subject.department
            ):
                return True

        elif isinstance(user, OrganizationUser):
            # Organizační uživatel má přístup k dokumentům praxí své organizace
            if not sp.practice:
                return False
            employer_profile = getattr(user, "employer_profile", None)
            return sp.practice.employer == employer_profile

        return False
