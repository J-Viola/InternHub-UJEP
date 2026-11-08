"""STAG ticket v JWT claimu.

Ticket se nikdy neukládá do databáze. Při STAG loginu se zašifruje Fernetem
a vloží jako claim ``stg`` do refresh tokenu (access token claim převezme).
Server ho z claimu dešifruje jen pro volání STAGu; klient hodnotu nepřečte.

Ven se nikdy nedostane plaintext ani v logu — logují se jen chyby bez obsahu.
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from users.models import InvalidStagTicketError

CLAIM_NAME = "stg"


def _fernet() -> Fernet:
    return Fernet(settings.STAG_TICKET_ENCRYPTION_KEY.encode())


def encrypt_ticket(ticket: str) -> str:
    """Zašifruje ticket pro uložení do JWT claimu. Prázdný ticket zůstane prázdný."""
    if not ticket:
        return ""
    return _fernet().encrypt(ticket.encode()).decode()


def decrypt_ticket(value: str) -> str:
    """Dešifruje claim; neplatný nebo cizí token vyhodí ``InvalidStagTicketError``."""
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, TypeError, ValueError) as exc:
        raise InvalidStagTicketError("STAG ticket v tokenu není platný.") from exc


def ticket_from_token(token) -> str:
    """Vrátí dešifrovaný ticket z ověřeného JWT, nebo ``""`` když claim chybí."""
    if not token:
        return ""
    payload = getattr(token, "payload", None)
    if not isinstance(payload, dict):
        payload = token if isinstance(token, dict) else {}
    return decrypt_ticket(payload.get(CLAIM_NAME) or "")
