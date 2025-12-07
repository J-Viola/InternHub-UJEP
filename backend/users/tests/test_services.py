from unittest.mock import MagicMock, patch

from django.test import TestCase

from users.dtos.dtos import EkonomickySubjektDTO
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser
from users.services import register_organization, update_organization_from_ares


class UserServiceTests(TestCase):
    def setUp(self):
        self.valid_register_data = {
            "email": "org@test.com",
            "password": "password123",
            "first_name": "Org",
            "last_name": "Owner",
            "ico": "12345678",
            "companyName": "Test Corp",
            "address": "Test St 123",
            "dic": "CZ12345678",
        }

    @patch("users.services.fetch_ares_data")
    def test_register_organization_success(self, mock_fetch_ares):
        # Mock ARES data
        mock_ares_dto = MagicMock(spec=EkonomickySubjektDTO)
        # Set attributes that might be accessed
        mock_ares_dto.dic = "CZ12345678"
        mock_ares_dto.obchodniJmeno = "ARES Corp"
        # mock_ares_dto.sidlo... (if needed)
        mock_fetch_ares.return_value = mock_ares_dto

        user = register_organization(self.valid_register_data)

        self.assertIsInstance(user, OrganizationUser)
        self.assertEqual(user.email, "org@test.com")
        self.assertTrue(EmployerProfile.objects.filter(employer_id=user.id).exists())
        profile = EmployerProfile.objects.get(employer_id=user.id)
        self.assertEqual(profile.ico, "12345678")
        self.assertEqual(profile.company_name, "Test Corp")  # Should use provided name over ARES if provided
        self.assertEqual(profile.approval_status, ApprovalStatus.PENDING)

    @patch("users.services.fetch_ares_data")
    def test_register_organization_ares_fail(self, mock_fetch_ares):
        mock_fetch_ares.return_value = None

        with self.assertRaises(ValueError):
            register_organization(self.valid_register_data)

    @patch("users.services.fetch_ares_data")
    def test_update_organization_from_ares_success(self, mock_fetch_ares):
        # Setup existing user
        user = OrganizationUser.objects.create(email="update@test.com", first_name="U", last_name="D")

        # Mock ARES
        mock_ares_dto = MagicMock(spec=EkonomickySubjektDTO)
        mock_ares_dto.ico = "87654321"
        mock_ares_dto.dic = "CZ87654321"
        mock_ares_dto.obchodniJmeno = "Updated Corp"
        sidlo_mock = MagicMock()
        sidlo_mock.textovaAdresa = "New Address 1"
        sidlo_mock.psc = 12345
        mock_ares_dto.sidlo = sidlo_mock

        mock_fetch_ares.return_value = mock_ares_dto

        # Call service
        update_organization_from_ares(user, "87654321")

        # Verify
        profile = EmployerProfile.objects.get(employer_id=user.id)
        self.assertEqual(profile.ico, "87654321")
        self.assertEqual(profile.company_name, "Updated Corp")
        self.assertEqual(profile.address, "New Address 1")
