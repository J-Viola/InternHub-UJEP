# BL-05 / C21-A — závazný číselník „typ úvazku" (guarantor-values.md §1, 2026-10-11).
#
# - AlterField: choices z PLACEHOLDER na závazné kódy (models.EMPLOYMENT_TYPE_CHOICES).
# - RunPython: normalizace uložených placeholder kódů → uvazek_0_5 / uvazek_1_0
#   (pre-production, nízké riziko dle rozhodnutí; reverzní funkce mapuje zpět).
#   Řádky s prázdným úvazkem (default "") se nemění.
# Historický snapshot 0013 se NEupravuje — tento krok ho přebíjí.

from django.db import migrations, models

EMPLOYMENT_TYPE_CHOICES = [
    ("uvazek_0_5", "Úvazek 0,5"),
    ("uvazek_1_0", "Úvazek 1,0"),
]

# Legacy (BL-05 placeholder) → autoritativní kód; musí souhlasit s
# practices.models.EMPLOYMENT_TYPE_LEGACY_CODE_MAP (pokryto testem).
LEGACY_TO_CANONICAL = {
    "placeholder_part_time": "uvazek_0_5",
    "placeholder_full_time": "uvazek_1_0",
}


def apply_employment_type_map(PracticeModel, code_map):
    """Aplikuje mapu kódů na model (sdíleno s legacy mapping testem)."""
    for old_code, new_code in code_map.items():
        PracticeModel.objects.filter(employment_type=old_code).update(employment_type=new_code)


def map_placeholder_codes(apps, schema_editor):
    Practice = apps.get_model("practices", "Practice")
    apply_employment_type_map(Practice, LEGACY_TO_CANONICAL)


def unmap_placeholder_codes(apps, schema_editor):
    """Reverze: autoritativní kódy zpět na placeholder (náhodné nouzové vrácení)."""
    Practice = apps.get_model("practices", "Practice")
    apply_employment_type_map(Practice, {v: k for k, v in LEGACY_TO_CANONICAL.items()})


class Migration(migrations.Migration):
    dependencies = [
        ("practices", "0013_practice_employment_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="practice",
            name="employment_type",
            field=models.CharField(
                blank=True,
                choices=EMPLOYMENT_TYPE_CHOICES,
                db_index=True,
                default="",
                help_text=("Typ úvazku nabídky. Závazný číselník dle rozhodnutí garantů/vlastníka (guarantor-values.md, 2026-10-11)."),
                max_length=64,
            ),
        ),
        migrations.RunPython(map_placeholder_codes, unmap_placeholder_codes),
    ]
