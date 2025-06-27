# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    ActionLog,
    Department,
    DepartmentUserRole,
    EmployerInvitation,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    Practice,
    PracticeType,
    PracticeUser,
    Role,
    StagRole,
    StagUser,
    Status,
    StudentPractice,
    Subject,
    UploadedDocument,
    User,
    UserSubject,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


admin.site.register(Status)
admin.site.register(Role)
admin.site.register(StagRole)
admin.site.register(OrganizationRole)
admin.site.register(EmployerProfile)
admin.site.register(OrganizationUser)
admin.site.register(StagUser)
admin.site.register(ActionLog)
admin.site.register(Department)
admin.site.register(DepartmentUserRole)
admin.site.register(Subject)
admin.site.register(EmployerInvitation)
admin.site.register(PracticeType)
admin.site.register(Practice)
admin.site.register(PracticeUser)
admin.site.register(StudentPractice)
admin.site.register(UploadedDocument)
admin.site.register(UserSubject)
