# Generated by Django 5.2.4 on 2025-07-07 16:30

import api.models
import django_enumfield.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0013_rename_ucitidno_professoruser_ucit_idno"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employerinvitation",
            name="status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.EmployerInvitationStatus
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="employerprofile",
            name="approval_status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.ApprovalStatus
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="practice",
            name="approval_status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.ApprovalStatus
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="practice",
            name="status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.ProgressStatus
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="studentpractice",
            name="approval_status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.ApprovalStatus
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="studentpractice",
            name="progress_status",
            field=django_enumfield.db.fields.EnumField(
                default=0, enum=api.models.ProgressStatus
            ),
            preserve_default=False,
        ),
    ]
