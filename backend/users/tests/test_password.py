from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import OrganizationUser, StagUser

User = get_user_model()


class ChangePasswordViewTests(APITestCase):
    def setUp(self):
        # Create a standard user (OrganizationUser is suitable as it uses internal password auth)
        self.user = OrganizationUser.objects.create_user(
            email="test@org.com",
            password="OldPassword123",
            first_name="Test",
            last_name="Org",
            is_active=True,
        )
        self.url = reverse("users:change-password")

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "old_password": "OldPassword123",
            "new_password": "NewPassword456",
            "new_password_confirm": "NewPassword456",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword456"))

    def test_change_password_incorrect_old(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "old_password": "WrongPassword",
            "new_password": "NewPassword456",
            "new_password_confirm": "NewPassword456",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)

    def test_change_password_mismatch(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "old_password": "OldPassword123",
            "new_password": "NewPassword456",
            "new_password_confirm": "MismatchPassword",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_confirm", response.data.get("details", {}))

    def test_stag_user_cannot_change_password(self):
        stag_user = StagUser.objects.create(email="stag@ujep.cz", is_active=True)
        self.client.force_authenticate(user=stag_user)
        data = {
            "old_password": "OldPassword123",
            "new_password": "NewPassword456",
            "new_password_confirm": "NewPassword456",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        self.user = OrganizationUser.objects.create_user(
            email="reset@org.com",
            password="OldPassword123",
            first_name="Reset",
            last_name="User",
            is_active=True,
        )
        self.request_url = reverse("users:password-reset-request")
        self.confirm_url = reverse("users:password-reset-confirm")

    def test_request_reset_email_sent(self):
        data = {"email": "reset@org.com"}
        response = self.client.post(self.request_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password", mail.outbox[0].body)
        self.assertIn("reset@org.com", mail.outbox[0].to)

    def test_request_reset_invalid_email(self):
        # Should return 200 OK for security reasons, but send no email
        data = {"email": "nonexistent@org.com"}
        response = self.client.post(self.request_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_confirm_success(self):
        # Generate valid tokens manually
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        data = {
            "uidb64": uid,
            "token": token,
            "new_password": "NewStrongPassword123",
            "new_password_confirm": "NewStrongPassword123",
        }
        response = self.client.post(self.confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123"))

    def test_reset_confirm_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        data = {
            "uidb64": uid,
            "token": "invalid-token",
            "new_password": "NewStrongPassword123",
            "new_password_confirm": "NewStrongPassword123",
        }
        response = self.client.post(self.confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
