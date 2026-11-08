"""Sdílené validátory backend API (použito např. u Practice.external_details_file)."""

import zipfile

from django.core.exceptions import ValidationError

from api.models import SystemSettings


def validate_file_size(value):
    """
    Ověří, že nahraný soubor nepřesahuje ``SystemSettings.max_upload_size`` (výchozí 10 MB).

    Limit se čte z settings (žádný hardcode). Sdíleno přes backend/api —
    sjednotí duplicitní kontroly v student_practices/views.py na tento validátor.
    """
    limit = SystemSettings.get_solo().max_upload_size
    if value is not None and getattr(value, "size", None) is not None and value.size > limit:
        mb = limit // (1024 * 1024)
        raise ValidationError(f"Soubor překračuje maximální povolenou velikost {mb} MB.")


def validate_file_content(value):
    """Validate PDF/DOCX signatures; legacy .doc content is intentionally unchecked."""
    if value is None:
        return
    name = getattr(value, "name", "").lower()
    try:
        value.seek(0)
        if name.endswith(".pdf"):
            if value.read(4) != b"%PDF":
                raise ValidationError("Obsah souboru neodpovídá formátu PDF.")
        elif name.endswith(".docx"):
            try:
                value.seek(0)
                with zipfile.ZipFile(value) as archive:
                    if not any(item.startswith("word/") for item in archive.namelist()):
                        raise ValidationError("Soubor DOCX neobsahuje dokument Word.")
            except zipfile.BadZipFile as exc:
                raise ValidationError("Soubor DOCX není platný ZIP dokument.") from exc
    finally:
        value.seek(0)
