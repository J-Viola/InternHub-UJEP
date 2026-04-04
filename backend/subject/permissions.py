from rest_framework import permissions

from users.models import ProfessorUser


class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return isinstance(request.user, ProfessorUser)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
