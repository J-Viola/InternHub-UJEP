from enum import Enum
from functools import wraps

from api.models import OrganizationRole, OrganizationUser, StagUser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenBackendError, TokenError
from users.models import StagRoleEnum


def role_required(allowed_enums: list[Enum]):
    """
    Decorator that restricts access based on user roles.

    Args:
        allowed_enums: List of StagRoleEnum or OrganizationRole enum values

    Usage:
        @role_required([StagRoleEnum.ADMIN, OrganizationRole.OWNER])
        def my_view(request):
            ...
    """
    if not allowed_enums or not all(isinstance(r, (StagRoleEnum, OrganizationRole)) for r in allowed_enums):
        raise ValueError("allowed_enums must be members of StagRoleEnum or OrganizationRole")

    allowed_roles = {r.value for r in allowed_enums}

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # Authenticate user
            auth = JWTAuthentication()
            try:
                user_auth = auth.authenticate(request)
            except (AuthenticationFailed, TokenError, TokenBackendError) as e:
                raise NotAuthenticated("Invalid or missing credentials")

            if not user_auth:
                raise NotAuthenticated("Authentication credentials were not provided")

            user, token = user_auth
            request.user, request.auth = user, token

            # Check permissions
            has_permission = (
                user.is_superuser
                or (isinstance(user, OrganizationUser) and user.organization_role in allowed_roles)
                or (isinstance(user, StagUser) and user.stag_role.role in allowed_roles)
            )

            if has_permission:
                return view_func(self, request, *args, **kwargs)

            raise PermissionDenied("You do not have permission to access this resource")

        return _wrapped_view

    return decorator
