from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from api.models import SystemParameter
        from api.parameter_service import invalidate_param_cache

        post_save.connect(
            lambda sender, instance, **kwargs: invalidate_param_cache(instance.key),
            sender=SystemParameter,
            dispatch_uid="system_parameter_save",
        )
        post_delete.connect(
            lambda sender, instance, **kwargs: invalidate_param_cache(instance.key),
            sender=SystemParameter,
            dispatch_uid="system_parameter_delete",
        )

    label = "api"
