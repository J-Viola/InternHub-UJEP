# BL-05 / RF-02a — explicitní „typ úvazku" (employment type) filtr nabídek.
# Ručně dopsáno v audit lane (verification settings má MIGRATION_MODULES
# zakázané, makemigrations jej tedy nemohl zapsat). Odpovídá definici
# Practice.employment_type v practices/models.py.
#
# PLACEHOLDER číselník — závazné hodnoty dodají garanti KI/KMA (C21-A).

from django.db import migrations, models

EMPLOYMENT_TYPE_PLACEHOLDER_CHOICES = [
    ("placeholder_part_time", "Úvazek 0,5 [PLACEHOLDER — čeká na číselník garanta]"),
    ("placeholder_full_time", "Úvazek 1,0 [PLACEHOLDER — čeká na číselník garanta]"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("practices", "0012_practice_contact_email_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="practice",
            name="employment_type",
            field=models.CharField(
                blank=True,
                choices=EMPLOYMENT_TYPE_PLACEHOLDER_CHOICES,
                db_index=True,
                default="",
                help_text=(
                    "Typ úvazku nabídky. PLACEHOLDER číselník — závazné hodnoty "
                    "dodají garanti KI/KMA (rozhodnutí C21-A)."
                ),
                max_length=64,
            ),
        ),
    ]
