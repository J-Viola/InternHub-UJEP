"""A-10 — STAG ticket žije jen v šifrovaném JWT claimu, nikdy v databázi."""

from unittest import mock

from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from users.jwt_tokens import REDACTED_TOKEN, RedactedRefreshToken, RedactedTokenRefreshSerializer
from users.models import InvalidStagTicketError, StagUser, StudentUser, User
from users.serializers import CustomTokenObtainPairSerializer
from users.services import fetch_student_data_from_stag
from users.stag_ticket import CLAIM_NAME, decrypt_ticket, encrypt_ticket, ticket_from_token
from users.tokens import revoke_refresh_tokens


@override_settings(STAG_MOCK=False, DEMO_LOGIN=False)
class StagTicketClaimTests(TestCase):
    def setUp(self):
        self.student = StudentUser.objects.create(email="a10@test.local", os_cislo="A10", is_active=True)

    def test_model_has_no_ticket_field(self):
        with self.assertRaises(FieldDoesNotExist):
            StagUser._meta.get_field("stag_ticket")

    def test_claim_roundtrip_has_no_plaintext(self):
        encrypted = encrypt_ticket("abc123")
        self.assertNotIn("abc123", encrypted)
        self.assertEqual(decrypt_ticket(encrypted), "abc123")

    def test_tampered_claim_is_rejected(self):
        with self.assertRaises(InvalidStagTicketError):
            decrypt_ticket("plaintext-ticket")

    def test_refresh_token_carries_claim_into_access_token(self):
        token = RefreshToken.for_user(self.student)
        token[CLAIM_NAME] = encrypt_ticket("abc123")
        self.assertEqual(ticket_from_token(token), "abc123")
        self.assertEqual(ticket_from_token(token.access_token), "abc123")

    def test_refresh_rotation_keeps_claim(self):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        token = RefreshToken.for_user(self.student)
        token[CLAIM_NAME] = encrypt_ticket("abc123")
        data = TokenRefreshSerializer().validate({"refresh": str(token)})
        self.assertEqual(ticket_from_token(AccessToken(data["access"])), "abc123")
        self.assertEqual(ticket_from_token(RefreshToken(data["refresh"])), "abc123")

    def test_fetch_without_ticket_skips_stag(self):
        with mock.patch("users.services.get_stag_client") as client:
            self.assertEqual(fetch_student_data_from_stag(self.student), {})
        client.return_value.get_student_info.assert_not_called()

    def test_fetch_with_ticket_calls_stag(self):
        with mock.patch("users.services.get_stag_client") as client:
            client.return_value.get_student_info.return_value = {}
            fetch_student_data_from_stag(self.student, ticket="abc123")
        client.return_value.get_student_info.assert_called_once_with("abc123", "A10")

    def test_revoke_refresh_tokens_blacklists_outstanding(self):
        RefreshToken.for_user(self.student)
        self.assertGreaterEqual(revoke_refresh_tokens(self.student), 1)
        self.assertTrue(BlacklistedToken.objects.filter(token__user=self.student).exists())


class StagLoginClaimTests(TestCase):
    def setUp(self):
        self.serializer = CustomTokenObtainPairSerializer()

    @mock.patch("users.serializers.get_or_create_stag_user")
    @mock.patch("users.serializers.validate_stag_ticket")
    def test_login_puts_encrypted_ticket_into_tokens(self, mock_validate, mock_get_user):
        mock_validate.return_value = {"some": "data"}
        user = StudentUser.objects.create(email="claim@test.local", os_cislo="C1", is_active=True)
        mock_get_user.return_value = user

        result = self.serializer.validate({"service_ticket": "valid-ticket"})

        self.assertNotIn("valid-ticket", result["refresh"])
        self.assertEqual(ticket_from_token(RefreshToken(result["refresh"])), "valid-ticket")
        self.assertEqual(ticket_from_token(AccessToken(result["access"])), "valid-ticket")


class StagLogoutInvalidationTests(TestCase):
    def setUp(self):
        self.student = StudentUser.objects.create(email="logout@test.local", os_cislo="L1", is_active=True)

    def test_real_client_calls_invalidate_ticket(self):
        from users.stag_api.real_client import RealStagClient

        with (
            override_settings(STAG_WS_URL="https://stag.example/ws"),
            mock.patch("users.stag_api.real_client.requests.get") as get,
        ):
            get.return_value.status_code = 200
            RealStagClient().invalidate_ticket("abc123")

        url = get.call_args.args[0]
        self.assertTrue(url.endswith("/services/rest2/help/invalidateTicket"))
        self.assertEqual(get.call_args.kwargs["params"], {"ticket": "abc123"})

    def test_real_client_raises_on_non_200(self):
        from users.stag_api.exceptions import StagUnreachableError
        from users.stag_api.real_client import RealStagClient

        with (
            override_settings(STAG_WS_URL="https://stag.example/ws"),
            mock.patch("users.stag_api.real_client.requests.get") as get,
        ):
            get.return_value.status_code = 500
            with self.assertRaises(StagUnreachableError):
                RealStagClient().invalidate_ticket("abc123")

    def _client_with_ticket(self):
        token = RefreshToken.for_user(self.student)
        token[CLAIM_NAME] = encrypt_ticket("abc123")
        client = APIClient()
        client.force_authenticate(user=self.student)
        client.cookies["refresh_token"] = str(token)
        return client

    def test_logout_invalidates_ticket_in_stag(self):
        with mock.patch("users.views.get_stag_client") as get_client:
            response = self._client_with_ticket().post(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)
        get_client.return_value.invalidate_ticket.assert_called_once_with("abc123")

    def test_stag_failure_does_not_block_logout(self):
        with mock.patch("users.views.get_stag_client") as get_client:
            get_client.return_value.invalidate_ticket.side_effect = RuntimeError("STAG down")
            response = self._client_with_ticket().post(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)

    def test_logout_without_claim_does_not_call_stag(self):
        token = RefreshToken.for_user(self.student)
        client = APIClient()
        client.force_authenticate(user=self.student)
        client.cookies["refresh_token"] = str(token)
        with mock.patch("users.views.get_stag_client") as get_client:
            response = client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)
        get_client.return_value.invalidate_ticket.assert_not_called()

    def test_logout_with_corrupt_claim_does_not_fail(self):
        token = RefreshToken.for_user(self.student)
        token[CLAIM_NAME] = "not-a-fernet-token"
        client = APIClient()
        client.force_authenticate(user=self.student)
        client.cookies["refresh_token"] = str(token)
        with mock.patch("users.views.get_stag_client") as get_client:
            response = client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)
        get_client.return_value.invalidate_ticket.assert_not_called()


class PasswordChangeRevocationTests(TestCase):
    def test_password_change_blacklists_all_refresh_tokens(self):
        user = User.objects.create_user(email="pw@test.local", password="OldPassword123!", is_active=True)
        RefreshToken.for_user(user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            reverse("users:change-password"),
            {
                "old_password": "OldPassword123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            OutstandingToken.objects.filter(user=user).count(),
            BlacklistedToken.objects.filter(token__user=user).count(),
        )


class RedactedOutstandingTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="redact@test.local", password="OldPassword123!", is_active=True)

    def test_issued_token_is_redacted_in_db(self):
        token = RedactedRefreshToken.for_user(self.user)
        row = OutstandingToken.objects.get(jti=token["jti"])
        self.assertEqual(row.token, REDACTED_TOKEN)

    def test_rotation_redacts_new_token_and_keeps_claim(self):
        token = RedactedRefreshToken.for_user(self.user)
        token[CLAIM_NAME] = encrypt_ticket("abc123")

        data = RedactedTokenRefreshSerializer().validate({"refresh": str(token)})
        renewed = RedactedRefreshToken(data["refresh"])

        row = OutstandingToken.objects.get(jti=renewed["jti"])
        self.assertEqual(row.token, REDACTED_TOKEN)
        self.assertEqual(ticket_from_token(renewed), "abc123")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetRevocationTests(TestCase):
    def test_reset_confirm_blacklists_all_refresh_tokens(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = User.objects.create_user(email="reset@test.local", password="OldPassword123!", is_active=True)
        RefreshToken.for_user(user)

        client = APIClient()
        response = client.post(
            reverse("users:password-reset-confirm"),
            {
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            OutstandingToken.objects.filter(user=user).count(),
            BlacklistedToken.objects.filter(token__user=user).count(),
        )


class AnonymizeRevocationTests(TestCase):
    def test_anonymize_blacklists_all_refresh_tokens(self):
        from users.gdpr_service import GDPRService

        user = User.objects.create_user(email="anon@test.local", password="OldPassword123!", is_active=True)
        RefreshToken.for_user(user)

        GDPRService.anonymize_user(user)

        self.assertEqual(
            OutstandingToken.objects.filter(user=user).count(),
            BlacklistedToken.objects.filter(token__user=user).count(),
        )
