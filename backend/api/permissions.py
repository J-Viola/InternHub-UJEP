from rest_framework import permissions

from users.models import OrganizationRole, OrganizationUser, ProfessorUser, StagRoleEnum, StudentUser


class IsOrganizationUser(permissions.BasePermission):
    """
    Allows access only to Organization users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and isinstance(request.user, OrganizationUser)


class IsOrganizationOwner(permissions.BasePermission):
    """
    Allows access only to Organization owners.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and isinstance(request.user, OrganizationUser)
            and request.user.organization_role == OrganizationRole.OWNER
        )


class IsStagUser(permissions.BasePermission):
    """
    Allows access only to STAG users (Students or Professors).
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (isinstance(request.user, StudentUser) or isinstance(request.user, ProfessorUser))


class IsStagTeacher(permissions.BasePermission):
    """
    Allows access only to STAG users with role VY (Vyučující) or similar.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check if user has stag_role attribute (StudentUser/ProfessorUser)
        if not hasattr(request.user, "stag_role") or not request.user.stag_role:
            return False

        # Check against StagRoleEnum.VY
        # Note: role in StagRole model might be stored as string or enum depending on implementation
        role = request.user.stag_role.role
        return role == StagRoleEnum.VY or role == "VY"


class HasRolePermission(permissions.BasePermission):
    """
    Dynamic permission class factory usage is hard in simple class definition.
    This class checks if the view has a 'required_roles' attribute.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        required_roles = getattr(view, "required_roles", [])
        if not required_roles:
            return True

        # Check Organization Role
        if isinstance(request.user, OrganizationUser):
            return request.user.organization_role in required_roles

        # Check Stag Role
        if hasattr(request.user, "stag_role") and request.user.stag_role:
            return request.user.stag_role.role in required_roles

        return request.user.is_superuser
