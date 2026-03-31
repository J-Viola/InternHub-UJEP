# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_alter_organizationuser_managers_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersubject",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="usersubject",
            name="last_synced_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
