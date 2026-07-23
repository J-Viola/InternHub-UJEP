from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from users.gdpr_service import GDPRService
from users.models import StudentUser, UserConsent


class GDPRTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = StudentUser.objects.create_user(
            email="gdpr_test@example.com",
            password="Password123!",
            first_name="Jan",
            last_name="Novák",
        )
        self.consent = UserConsent.objects.create(
            user=self.user,
            consent_type="GDPR_TERMS",
            agreed=True,
        )

    def test_anonymize_user_service(self):
        GDPRService.anonymize_user(self.user)
        self.user.refresh_from_db()

        self.assertFalse(self.user.is_active)
        self.assertEqual(self.user.first_name, "Anonymized")
        self.assertIn("anonymized_", self.user.email)

    def test_export_user_data_service(self):
        data = GDPRService.export_user_data(self.user)
        self.assertEqual(data["user_info"]["email"], "gdpr_test@example.com")
        self.assertEqual(len(data["consents"]), 1)
        self.assertEqual(data["consents"][0]["type"], "GDPR_TERMS")

    def test_gdpr_export_api_endpoint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/users/me/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user_info", response.data)
        self.assertEqual(response.data["user_info"]["email"], "gdpr_test@example.com")

    def test_gdpr_anonymize_api_endpoint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/users/me/anonymize/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
