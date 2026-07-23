from django.db import migrations


def migrate_forward(apps, schema_editor):
    StudentPractice = apps.get_model("student_practices", "StudentPractice")

    # Map CONTRACTED -> AWAITING_CONTRACT or AWAITING_DOCUMENTS or keep CONTRACTED
    for sp in StudentPractice.objects.filter(workflow_state=3):  # 3 = CONTRACTED
        has_contract = sp.contract_document_id is not None
        has_content = sp.content_document_id is not None

        if not has_contract and not has_content:
            # Smlouva i obsah chybí -> AWAITING_CONTRACT (7)
            sp.workflow_state = 7
            sp.save(update_fields=["workflow_state"])
        elif has_contract and not has_content:
            # Smlouva existuje, ale obsah chybí -> AWAITING_DOCUMENTS (8)
            sp.workflow_state = 8
            sp.save(update_fields=["workflow_state"])

    # Map external practices in APPLIED state (0) -> AWAITING_CONTENT_APPROVAL (10)
    for sp in StudentPractice.objects.filter(workflow_state=0):
        if sp.practice and getattr(sp.practice, "is_external", False):
            sp.workflow_state = 10
            sp.save(update_fields=["workflow_state"])


def migrate_backward(apps, schema_editor):
    StudentPractice = apps.get_model("student_practices", "StudentPractice")

    # Map AWAITING_CONTRACT (7), AWAITING_DOCUMENTS (8), DOCUMENTS_REJECTED (9) back to CONTRACTED (3)
    StudentPractice.objects.filter(workflow_state__in=[7, 8, 9]).update(workflow_state=3)

    # Map AWAITING_CONTENT_APPROVAL (10), CONTENT_REJECTED (11), CONTENT_APPROVED (12) back to APPLIED (0)
    StudentPractice.objects.filter(workflow_state__in=[10, 11, 12]).update(workflow_state=0)


class Migration(migrations.Migration):
    dependencies = [
        ("student_practices", "0014_studentpractice_rejection_reason"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
