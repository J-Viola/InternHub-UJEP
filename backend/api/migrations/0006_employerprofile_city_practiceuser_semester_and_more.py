# Generated by Django 5.2.3 on 2025-06-29 16:23

import api.models
import django_enumfield.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_add_roles"),
    ]

    operations = [
        migrations.AddField(
            model_name="employerprofile",
            name="city",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="practiceuser",
            name="semester",
            field=django_enumfield.db.fields.EnumField(default=0, enum=api.models.SemesterType),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="practiceuser",
            name="year",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="staguser",
            name="os_cislo",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
