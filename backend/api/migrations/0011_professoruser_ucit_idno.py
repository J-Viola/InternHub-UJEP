# Generated by Django 5.2.4 on 2025-07-06 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_remove_staguser_additional_info_remove_staguser_city_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="professoruser",
            name="ucit_idno",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
