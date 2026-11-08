from django.db import migrations


class Migration(migrations.Migration):
    """STAG ticket se už neukládá do DB — nese ho jen šifrovaný JWT claim."""

    dependencies = [
        ("users", "0018_sign_or_clear_stag_tickets"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="staguser",
            name="stag_ticket",
        ),
    ]
