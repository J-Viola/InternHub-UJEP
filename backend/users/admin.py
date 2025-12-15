from django.contrib import admin
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from .models import (
    ActionLog,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    Role,
    StagRole,
    StudentUser,
    User,
)


@admin.register(StudentUser)
class StudentUserAdmin(PolymorphicChildModelAdmin):
    base_model = StudentUser
    show_in_index = True
    list_display = ("email", "first_name", "last_name", "os_cislo", "field_of_study", "year_of_study", "is_active")
    search_fields = ("email", "last_name", "os_cislo", "first_name")
    list_filter = ("is_active", "year_of_study", "field_of_study")


@admin.register(ProfessorUser)
class ProfessorUserAdmin(PolymorphicChildModelAdmin):
    base_model = ProfessorUser
    show_in_index = True
    list_display = ("email", "first_name", "last_name", "department", "department_role", "is_active")
    search_fields = ("email", "last_name")
    list_filter = ("is_active", "department")


@admin.register(OrganizationUser)
class OrganizationUserAdmin(PolymorphicChildModelAdmin):
    base_model = OrganizationUser
    show_in_index = True
    list_display = ("email", "full_name", "employer_profile", "organization_role", "is_active")
    search_fields = ("email", "last_name", "employer_profile__company_name")
    list_filter = ("is_active", "organization_role")


@admin.register(User)
class UserAdmin(PolymorphicParentModelAdmin):
    """
    The parent admin class for all user types.
    Allows filtering by user type (Student, Professor, Organization).
    """

    base_model = User
    child_models = (StudentUser, ProfessorUser, OrganizationUser)
    list_filter = (PolymorphicChildModelFilter, "is_active", "is_superuser", "is_staff")
    list_display = ("email", "first_name", "last_name", "is_active", "is_superuser", "polymorphic_ctype")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # Přesměruje na správný child admin formulář, pokud se jedná o child model
    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        if obj and type(obj) is User:
            # Pokud je objekt typu User, ale měl by být Child,
            # pokusíme se ho načíst jako Child.
            for child_model in self.child_models:
                try:
                    child_obj = child_model._default_manager.get(pk=obj.pk)
                    return child_obj
                except child_model.DoesNotExist:
                    continue
        return obj

    # Zamezíme vytváření/editaci základního User modelu
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and type(obj) is User and not any(isinstance(obj, cm.base_model) for cm in self.child_models):
            return False  # Zakázat editaci čistého User objektu
        return super().has_change_permission(request, obj)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "ico", "city", "approval_status", "created_at")
    list_filter = ("approval_status", "created_at")
    search_fields = ("company_name", "ico", "dic")
    ordering = ("company_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StagRole)
class StagRoleAdmin(admin.ModelAdmin):
    list_display = ("role", "role_name", "description")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_name", "description")


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ("action_date", "user", "action_type", "object_type", "action_description")
    list_filter = ("action_type", "object_type", "action_date")
    search_fields = ("user__email", "action_description")
    readonly_fields = ("action_date", "user", "action_type", "object_type", "object_id", "action_description")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
