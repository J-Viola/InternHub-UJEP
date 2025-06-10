from enum import Enum
from functools import wraps

from api.models import OrganizationUser, StagUser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from users.models import OrganizationRoleEnum, StagRoleEnum


def role_required(allowed_Enums: list[Enum]):
    """
    Decorator factory that restricts access based on the 'type' claim in JWT.
    Usage:
        @role_required(['admin', 'manager'])
        def my_view(request):
            ...
    """
    if not allowed_Enums or not all(isinstance(r, (StagRoleEnum, OrganizationRoleEnum)) for r in allowed_Enums):
        raise ValueError("allowed_roles must be members of StagRoleEnum or OrganizationRoleEnum")

    allowed_roles = {r.value for r in allowed_Enums}

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth = JWTAuthentication()
            try:
                user_auth = auth.authenticate(request)
            except Exception as e:
                print(f"JWT authentication error: {e}")
                raise NotAuthenticated("Invalid or missing credentials")
            if not user_auth:
                raise NotAuthenticated("Authentication credentials were not provided")
            user, token = user_auth
            request.user, request.auth = user, token

            if isinstance(user, OrganizationUser):
                role = user.organization_role.role
                if role not in allowed_roles:
                    raise PermissionDenied("You do not have permission to access this resource")
            if isinstance(user, StagUser):
                role = user.stag_role.role
                if role not in allowed_roles:
                    raise PermissionDenied("You do not have permission to access this resource")
            if user.is_superuser:
                pass
            else:
                raise NotAuthenticated("Authentication credentials were not provided")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
