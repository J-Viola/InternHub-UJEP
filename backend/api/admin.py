# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import (
    ActionLog,
    Department,
    EmployerInvitation,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    Practice,
    PracticeType,
    PracticeUser,
    ProfessorUser,
    Role,
    StagRole,
    StagUser,
    Status,
    StudentPractice,
    StudentUser,
    Subject,
    UploadedDocument,
    User,
    UserSubject,
)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("pk", "status_code", "status_name")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("pk", "role_name")


@admin.register(StagRole)
class StagRoleAdmin(admin.ModelAdmin):
    list_display = ("pk", "role_name", "role")


@admin.register(OrganizationRole)
class OrganizationRoleAdmin(admin.ModelAdmin):
    list_display = ("pk", "role_name", "role")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("pk", "company_name")


@admin.register(OrganizationUser)
class OrganizationUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")


@admin.register(StagUser)
class StagUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")


@admin.register(StudentUser)
class StudentUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")


@admin.register(ProfessorUser)
class ProfessorUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ("pk", "action_type", "action_date", "user")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("pk", "department_name")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("pk", "subject_code", "subject_name")


@admin.register(EmployerInvitation)
class EmployerInvitationAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "practice", "status")


@admin.register(PracticeType)
class PracticeTypeAdmin(admin.ModelAdmin):
    list_display = ("pk", "name")


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "employer", "subject", "status")


@admin.register(PracticeUser)
class PracticeUserAdmin(admin.ModelAdmin):
    list_display = ("pk", "practice", "user")


@admin.register(StudentPractice)
class StudentPracticeAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "practice", "approval_status")


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("pk", "document", "practice", "uploaded_at")


@admin.register(UserSubject)
class UserSubjectAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "subject", "role")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
