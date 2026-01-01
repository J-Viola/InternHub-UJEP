from rest_framework import permissions

from users.models import (
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRoleEnum,
    StagUser,
    StudentUser,
    UserSubjectType,
)


class IsOrganizationUser(permissions.BasePermission):
    """
    Allows access only to organization users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, OrganizationUser)
        )

    def has_object_permission(self, request, view, obj):
        # obj can be Practice or other models related to EmployerProfile
        if hasattr(obj, "employer"):
            return obj.employer == request.user.employer_profile
        if hasattr(obj, "employer_profile"):
            return obj.employer_profile == request.user.employer_profile
        return False


class IsOrganizationOwner(permissions.BasePermission):
    """
    Allows access only to organization owners.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, OrganizationUser)
            and request.user.organization_role == OrganizationRole.OWNER
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "employer"):
            return obj.employer == request.user.employer_profile
        if hasattr(obj, "employer_profile"):
            return obj.employer_profile == request.user.employer_profile
        return False


class IsStagUser(permissions.BasePermission):
    """
    Allows access only to STAG users (students or professors).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, StagUser)
        )


class IsStagStudent(permissions.BasePermission):
    """
    Allows access only to students (STAG role 'st').
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, StudentUser)
        )


class IsStagTeacher(permissions.BasePermission):
    """
    Allows access only to teachers (STAG role 'vy').
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, ProfessorUser)
        )


class IsStagAdmin(permissions.BasePermission):
    """
    Allows access only to STAG admins (STAG role 'vk' - department coordinator?).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, StagUser)
            and request.user.stag_role
            and request.user.stag_role.role == StagRoleEnum.VK.value
        )


class HasRolePermission(permissions.BasePermission):
    """
    Checks if the view's ``required_roles`` attribute contains the user's role.
    Returns True when the view defines no required_roles.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        required_roles = getattr(view, "required_roles", [])
        if not required_roles:
            return True

        if isinstance(request.user, OrganizationUser):
            return request.user.organization_role in required_roles

        if hasattr(request.user, "stag_role") and request.user.stag_role:
            return request.user.stag_role.role in required_roles

        return request.user.is_superuser


class CanViewStudentProfile(permissions.BasePermission):
    """
    Custom permission to allow access to student profile only for:
    - The student themselves
    - Admins
    - Organizations where the student applied or was invited
    - Professors from the same department (via subjects)
    """

    def has_permission(self, request, view):
        # Allow any authenticated user to try to access a student profile.
        # The specific object-level logic in has_object_permission will filter them.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # obj is StudentUser instance
        user = request.user

        # 1. Own profile
        if user == obj:
            return True

        # 2. Admin
        if user.is_superuser:
            return True

        # 3. Organization
        if isinstance(user, OrganizationUser) and user.employer_profile:
            # Check if student applied to any practice of this employer
            has_application = obj.student_practices.filter(
                practice__employer=user.employer_profile
            ).exists()
            # Check if student was invited by this employer
            has_invitation = obj.employer_invitations.filter(
                employer=user.employer_profile
            ).exists()

            if has_application or has_invitation:
                return True

        # 4. Professor
        if isinstance(user, ProfessorUser):
            from django.db.models import Q

            from users.services import get_user_department_ids

            dept_ids = get_user_department_ids(user)

            # Check if student is in any department the professor belongs to
            # OR if professor manages a subject the student is in
            has_subject = obj.user_subjects.filter(
                Q(subject__department_id__in=dept_ids)
                | Q(subject__subject_manager=user),
                role=UserSubjectType.Student,
            ).exists()

            if has_subject:
                return True

        return False
