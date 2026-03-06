from django.apps import AppConfig


class StudentPracticesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "student_practices"

    def ready(self):
        import student_practices.signals  # noqa: F401
