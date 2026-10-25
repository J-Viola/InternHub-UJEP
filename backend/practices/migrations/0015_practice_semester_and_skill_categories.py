from django.db import migrations, models


def categorize_legacy_skills(apps, schema_editor):
    Practice = apps.get_model("practices", "Practice")
    for practice in Practice.objects.all().only("practice_id", "skills").iterator():
        skills = practice.skills
        if isinstance(skills, list):
            practice.skills = {"technologies": skills, "tools": [], "methodologies": []}
            practice.save(update_fields=["skills"])


class Migration(migrations.Migration):
    dependencies = [("practices", "0014_practice_employment_type_codes")]

    operations = [
        migrations.AddField(
            model_name="practice",
            name="semester",
            field=models.CharField(
                blank=True,
                choices=[("ZS", "Zimní semestr"), ("LS", "Letní semestr")],
                default=None,
                max_length=2,
                null=True,
            ),
        ),
        migrations.RunPython(categorize_legacy_skills, migrations.RunPython.noop),
    ]
