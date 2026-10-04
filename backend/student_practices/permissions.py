from rest_framework import permissions

from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    StagRoleEnum,
    StudentUser,
    UserSubjectType,
)


class IsGarantForStudentPractice(permissions.BasePermission):
    """
    Povolí akci garanta nad StudentPractice (resolve-cancellation).

    Odpovídá rolové kontrole ``_check_transition_role`` (profesor VY/VK nebo
    ``is_garant_praxe``) + objektové kontrole departmentu:
    garant smí zasahovat jen do praxí svého departmentu.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if isinstance(user, ProfessorUser):
            stag_role = getattr(user, "stag_role", None)
            if (
                stag_role
                and getattr(stag_role, "role", "")
                and str(stag_role.role).lower()
                in (
                    StagRoleEnum.VY,
                    StagRoleEnum.VK,
                )
            ):
                return True
            if getattr(user, "is_garant_praxe", False):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        practice = getattr(obj, "practice", obj)
        subject = getattr(practice, "subject", None)
        if subject is None:
            return False

        user_dept_id = getattr(user, "department_id", None)
        if user_dept_id is not None and subject.department_id == user_dept_id:
            return True
        user_dept = getattr(user, "department", None)
        if user_dept is not None and subject.department_id == user_dept.pk:
            return True
        return False


class IsOrganizationApproverForStudentPractice(permissions.BasePermission):
    """
    Organizace (vlastník praxe) smí provádět přechody stavu StudentPractice
    (PRELIMINARY_APPROVED → AWAITING_CONTRACT/CONTRACTED/REJECTED).

    Objektová kontrola: organizace = employer praxe dané přihlášky.
    (DRF 3.17 OR kombinace vyžaduje has_permission AND has_object_permission —
    proto má tato třída obě metody; IsOrganizationUser.has_object_permission
    neumí StudentPractice.)
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and isinstance(user, OrganizationUser) and getattr(user, "employer_profile", None))

    def has_object_permission(self, request, view, obj):
        user = request.user
        practice = getattr(obj, "practice", obj)
        if practice is None:
            return False
        return bool(getattr(practice, "employer", None) and getattr(practice, "employer", None) == getattr(user, "employer_profile", None))


class IsSubjectTeacherOrHeadForPractice(permissions.BasePermission):
    """
    Umožní přístup, pokud je uživatel oprávněn schválit danou praxi (Učitel/Vedoucí).

    Object-level only — view must call check_object_permissions().
    has_permission defaults to True (class-level gate is a pass-through).
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
            is_professor_for_subject = user_subjects.filter(user=user, role=UserSubjectType.Professor).exists()
            if is_professor_for_subject:
                return True

            # Check if professor is head of the department
            if user.department_role == DepartmentRole.HEAD and user.department == subject.department:
                return True

        elif isinstance(user, OrganizationUser):
            # Organizační uživatel má přístup k dokumentům praxí své organizace
            if not sp.practice:
                return False
            employer_profile = getattr(user, "employer_profile", None)
            return sp.practice.employer == employer_profile

        return False
