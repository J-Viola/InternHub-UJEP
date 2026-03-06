# Permissions are defined in users/permissions.py — this module re-exports them
# for backwards compatibility with existing imports.
from users.permissions import (  # noqa: F401
    CanViewStudentProfile,
    HasRolePermission,
    IsOrganizationOwner,
    IsOrganizationUser,
    IsStagAdmin,
    IsStagStudent,
    IsStagTeacher,
    IsStagUser,
)
