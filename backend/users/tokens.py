"""Revokace refresh tokenů při bezpečnostně citlivých změnách účtu."""

from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


@transaction.atomic
def revoke_refresh_tokens(user) -> int:
    """
    Zneplatní všechny vydané refresh tokeny uživatele.

    Používá se při změně hesla, resetu hesla a anonymizaci účtu, aby starší
    relace nemohly dál obnovovat access token. Vrací počet nově zneplatněných.
    """
    revoked = 0
    tokens = OutstandingToken.objects.select_for_update().filter(user=user)
    for token in list(tokens):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        revoked += int(created)
    return revoked
