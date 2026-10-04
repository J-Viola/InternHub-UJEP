"""Sdílené validátory backend API (použito např. u Practice.external_details_file)."""

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_size(value):
    """
    Ověří, že nahraný soubor nepřesahuje ``settings.MAX_UPLOAD_SIZE`` (10 MB).

    Limit se čte z settings (žádný hardcode). Sdíleno přes backend/api —
    sjednotí duplicitní kontroly v student_practices/views.py na tento validátor.
    """
    limit = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    if value is not None and getattr(value, "size", None) is not None and value.size > limit:
        mb = limit // (1024 * 1024)
        raise ValidationError(f"Soubor přesahuje maximální povolenou velikost {mb} MB.")
