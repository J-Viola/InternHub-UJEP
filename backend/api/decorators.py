from enum import Enum
from functools import wraps

from api.models import OrganizationUser, StagUser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenBackendError, TokenError
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
        def _wrapped_view(self, request, *args, **kwargs):
            auth = JWTAuthentication()
            try:
                user_auth = auth.authenticate(request)
            except AuthenticationFailed as e:
                print(f"JWT authentication error: {e}")
                raise NotAuthenticated("Invalid or missing credentials")
            except TokenError as e:
                print(f"JWT authentication error: {e}")
                raise NotAuthenticated("Invalid or missing credentials")
            except TokenBackendError as e:
                print(f"JWT authentication error: {e}")
                raise NotAuthenticated("Invalid or missing credentials")
            if not user_auth:
                raise NotAuthenticated("Authentication credentials were not provided")
            user, token = user_auth
            request.user, request.auth = user, token

            if (
                user.is_superuser
                or (isinstance(user, OrganizationUser) and user.organization_role.role in allowed_roles)
                or (isinstance(user, StagUser) and user.stag_role.role in allowed_roles)
            ):
                return view_func(self, request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to access this resource")

        return _wrapped_view

    return decorator
