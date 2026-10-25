import re

import django_enumfield.db.fields
from django.db import migrations

import student_practices.models

STATE_BY_NAME = {
    "APPLIED": 0,
    "PRELIMINARY_APPROVED": 1,
    "REJECTED": 2,
    "CONTRACTED": 3,
    "STARTED": 4,
    "ENDED": 5,
    "COMPLETED": 6,
    "AWAITING_CONTRACT": 7,
    "AWAITING_DOCUMENTS": 8,
    "DOCUMENTS_REJECTED": 9,
    "AWAITING_CONTENT_APPROVAL": 10,
    "CONTENT_REJECTED": 11,
    "CONTENT_APPROVED": 12,
    "DOCUMENTS_RESUBMITTED": 13,
}


def backfill_cancelled_from_state(apps, schema_editor):
    StudentPractice = apps.get_model("student_practices", "StudentPractice")
    ActionLog = apps.get_model("users", "ActionLog")
    using = schema_editor.connection.alias
    pattern = re.compile(r"původní stav:\s*([A-Z_]+)")
    queryset = StudentPractice.objects.using(using).filter(is_cancelled=True, cancelled_from_state__isnull=True)
    while True:
        batch = list(queryset.order_by("pk")[:500])
        if not batch:
            break
        state_by_id = {}
        logs = ActionLog.objects.using(using).filter(
            object_type="StudentPractice", object_id__in=[sp.pk for sp in batch], action_type="STORNO"
        ).order_by("-action_date", "-pk").values_list("object_id", "action_description")
        for object_id, description in logs:
            if object_id in state_by_id:
                continue
            match = pattern.search(description or "")
            if match and match.group(1) in STATE_BY_NAME:
                state_by_id[object_id] = STATE_BY_NAME[match.group(1)]
        for sp in batch:
            if sp.pk in state_by_id:
                sp.cancelled_from_state = state_by_id[sp.pk]
        StudentPractice.objects.using(using).bulk_update(
            [sp for sp in batch if sp.pk in state_by_id], ["cancelled_from_state"]
        )
        # Rows with no matching legacy ActionLog remain null; exclude this batch
        # from subsequent iterations to avoid looping forever.
        queryset = queryset.exclude(pk__in=[sp.pk for sp in batch])


class Migration(migrations.Migration):
    dependencies = [
        ("student_practices", "0025_backfill_studentpractice_year"),
        ("users", "0012_fix_model_issues"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentpractice",
            name="cancelled_from_state",
            field=django_enumfield.db.fields.EnumField(blank=True, enum=student_practices.models.StudentPracticeWorkflowState, null=True),
        ),
        migrations.RunPython(backfill_cancelled_from_state, migrations.RunPython.noop),
    ]
