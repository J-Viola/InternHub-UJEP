# from django.contrib import admin

# Register your models here.
from django.contrib import admin

from api.models import SystemParameter


@admin.register(SystemParameter)
class SystemParameterAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")
    search_fields = ("key", "description")
    readonly_fields = ("updated_at",)
