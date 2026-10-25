from django.db import migrations


def backfill_studentpractice_year(apps, schema_editor):
    """Fill missing years from application_date, falling back to start_date."""
    StudentPractice = apps.get_model("student_practices", "StudentPractice")
    using = schema_editor.connection.alias

    queryset = (
        StudentPractice.objects.using(using)
        .filter(year__isnull=True)
        .only("pk", "application_date", "start_date")
        .order_by("pk")
    )

    batch = []
    for practice in queryset.iterator(chunk_size=1000):
        anchor = practice.application_date or practice.start_date
        if anchor is None:
            continue
        practice.year = anchor.year
        batch.append(practice)
        if len(batch) >= 1000:
            StudentPractice.objects.using(using).bulk_update(batch, ["year"])
            batch.clear()

    if batch:
        StudentPractice.objects.using(using).bulk_update(batch, ["year"])


def noop_reverse(apps, schema_editor):
    # Restoring NULL would discard the derived year and cannot be reversed safely.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("student_practices", "0024_practiceregistration_studentpractice_registration_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_studentpractice_year, noop_reverse),
    ]
