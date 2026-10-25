from django.contrib import admin
from solo.admin import SingletonModelAdmin

from api.models import SystemSettings
from users.action_log import ActionLogService


@admin.register(SystemSettings)
class SystemSettingsAdmin(SingletonModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        old = {name: form.initial.get(name) for name in form.changed_data}
        super().save_model(request, obj, form, change)
        if form.changed_data:
            diff = "; ".join(f"{name}: {old[name]!r} → {getattr(obj, name)!r}" for name in form.changed_data)
            ActionLogService.log(request.user, "SYSTEM_SETTINGS_CHANGED", "SystemSettings", obj.pk, diff)
