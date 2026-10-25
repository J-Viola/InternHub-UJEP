from django.conf import settings
from django.db import migrations, models

PARAMETERS = {
    "PRACTICE_URGENCY_DAYS": [14, 7, 2],
    "PRACTICE_CREDIT_ALERT_DAYS": 14,
    "PRACTICE_CONTRACT_OVERDUE_DAYS": 7,
    "PRACTICE_APPROVAL_STALL_DAYS": 7,
    "MAX_UPLOAD_SIZE": 10 * 1024 * 1024,
}


def seed_parameters(apps, schema_editor):
    model = apps.get_model("api", "SystemParameter")
    db = schema_editor.connection.alias
    for key, default in PARAMETERS.items():
        value = getattr(settings, key, default)
        model.objects.using(db).update_or_create(
            key=key,
            defaults={"value": value, "description": f"Administrativní parametr {key}."},
        )


def remove_parameters(apps, schema_editor):
    apps.get_model("api", "SystemParameter").objects.using(schema_editor.connection.alias).filter(key__in=PARAMETERS).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SystemParameter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100, unique=True)),
                ("value", models.JSONField()),
                ("description", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.RunPython(seed_parameters, remove_parameters),
    ]
