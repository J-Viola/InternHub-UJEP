"""Refresh token bez použitelné kopie v databázi.

SimpleJWT ukládá při vydání a rotaci celý refresh token do ``OutstandingToken``.
Jakmile refresh token nese šifrovaný STAG ticket (claim ``stg``), dostal by se
ticket i do databáze. Řádky proto hned přepisujeme na redigovanou hodnotu;
blacklist používá pouze ``jti``, takže funkčnost zůstává.
"""

from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

REDACTED_TOKEN = "<redacted>"


class RedactedRefreshToken(RefreshToken):
    """Refresh token, který se v ``OutstandingToken`` neukládá v použitelné podobě."""

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        cls._redact(token)
        return token

    def outstand(self):
        result = super().outstand()
        self._redact(self)
        return result

    @staticmethod
    def _redact(token):
        OutstandingToken.objects.filter(jti=token["jti"]).update(token=REDACTED_TOKEN)


class RedactedTokenRefreshSerializer(TokenRefreshSerializer):
    token_class = RedactedRefreshToken
