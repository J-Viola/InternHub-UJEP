# Generated by Django 5.2.4 on 2025-07-06 17:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_professoruser_ucit_idno"),
    ]

    operations = [
        migrations.RenameField(
            model_name="professoruser",
            old_name="ucit_idno",
            new_name="ucitIdno",
        ),
    ]
