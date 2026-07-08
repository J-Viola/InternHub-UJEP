# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_restore_user_manager"),
    ]

    operations = [
        migrations.AlterField(
            model_name="staguser",
            name="stag_ticket",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Šifrovaný dočasný STAG ticket (uložen při loginu pro on-demand fetch student info).",
                max_length=700,
            ),
        ),
    ]
