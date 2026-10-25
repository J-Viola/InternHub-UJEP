"""A-10 — nepodepsané (plaintext) nebo poškozené STAG tickety se vynulují.

Varianta „vynulovat“: tickety jsou krátkodobé (platnost řádově minuty/hodiny),
takže podepisování starých hodnot nemá smysl; uživatel se přihlásí znovu.
Zpětná migrace je no-op (vynulovaný ticket nelze obnovit).
"""

from django.core.signing import BadSignature, Signer
from django.db import migrations


def clear_unsigned_tickets(apps, schema_editor):
    StagUser = apps.get_model("users", "StagUser")
    signer = Signer(salt="stag_ticket_encryption")
    for pk, ticket in StagUser.objects.exclude(stag_ticket="").values_list(
        "pk", "stag_ticket"
    ):
        try:
            signer.unsign(ticket)
        except BadSignature:
            StagUser.objects.filter(pk=pk).update(stag_ticket="")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0017_employerprofile_manual_ares_entry"),
    ]

    operations = [
        migrations.RunPython(clear_unsigned_tickets, migrations.RunPython.noop),
    ]
