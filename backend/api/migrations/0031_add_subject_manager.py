# Generated manually on 2025-10-14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0030_remove_practice_practice_type_practice_coefficient_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="subject_manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="managed_subjects",
                to="api.professoruser",
            ),
        ),
    ]
