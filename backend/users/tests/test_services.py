from unittest.mock import MagicMock, patch

from django.test import TestCase
from notifications.models import Notification, NotificationType

from users.dtos.dtos import Adresa, EkonomickySubjektDTO
from users.models import ApprovalStatus, OrganizationUser
from users.services import AresUnavailableError, register_organization, update_organization_from_ares


def _execute_on_commit(mock_on_commit):
    """Test helper: transaction.on_commit callbacks se vykonají synchronně."""
    mock_on_commit.side_effect = lambda func: func()


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

    def _create_garant(self):
        """Garant praxe (is_garant_praxe=True) na katedře KI — cíl notifikací."""
        from department.models import Department
        from users.models import ProfessorUser, StagRole, StagRoleEnum

        dept, _ = Department.objects.get_or_create(department_name="Informatika", department_code="KI")
        stag_role, _ = StagRole.objects.get_or_create(
            role=StagRoleEnum.VY,
            defaults={"role_name": "Vyučující"},
        )
        return ProfessorUser.objects.create(
            email="garant@test.com",
            first_name="Gar",
            last_name="Ant",
            is_active=True,
            department=dept,
            stag_role=stag_role,
            is_garant_praxe=True,
        )

    @patch("users.services.fetch_ares_data")
    def test_register_organization_success(self, mock_fetch_ares):
        # Mock ARES data (reálné DTO, aby pokrylo i pravniForma → legal_form)
        mock_fetch_ares.return_value = EkonomickySubjektDTO(
            ico="12345678",
            obchodniJmeno="ARES Corp",
            sidlo=Adresa(textovaAdresa="Test Address", psc=12345),
            dic="CZ12345678",
            pravniForma="Společnost s ručením omezeným",
        )

        user = register_organization(self.valid_register_data)

        self.assertIsInstance(user, OrganizationUser)
        self.assertEqual(user.email, "org@test.com")
        self.assertIsNotNone(user.employer_profile)
        profile = user.employer_profile
        self.assertEqual(profile.ico, "12345678")
        self.assertEqual(profile.company_name, "Test Corp")  # Should use provided name over ARES if provided
        self.assertEqual(profile.approval_status, ApprovalStatus.PENDING)

    @patch("users.services.fetch_ares_data")
    def test_register_organization_ares_fail(self, mock_fetch_ares):
        # ARES vrátil „subjekt nenalezen" (None) → registrace zůstává blokovaná
        mock_fetch_ares.return_value = None

        with self.assertRaises(ValueError):
            register_organization(self.valid_register_data)

    @patch("users.services.fetch_ares_data")
    @patch("users.services.transaction.on_commit")
    def test_register_organization_ares_outage_falls_back_to_manual_mode(self, mock_on_commit, mock_fetch_ares):
        """výpadek ARES (AresUnavailableError) NEBLOKUJE registraci."""
        _execute_on_commit(mock_on_commit)
        mock_fetch_ares.side_effect = AresUnavailableError("ARES timeout")
        garant = self._create_garant()

        user = register_organization(self.valid_register_data)

        profile = user.employer_profile
        self.assertIsNotNone(profile)
        self.assertTrue(profile.manual_ares_entry)
        self.assertFalse(profile.ares_locked)
        self.assertEqual(profile.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(profile.company_name, "Test Corp")  # čistě z klienta

        # varování garantům (in-app WARNING) — verb MANUAL_REGISTRATION
        manual_notifs = Notification.objects.filter(verb="MANUAL_REGISTRATION", recipient=garant)
        self.assertTrue(manual_notifs.exists())
        self.assertEqual(manual_notifs.first().notification_type, NotificationType.WARNING)
        # notifikace o nové registraci garantům (schvalovatelé)
        self.assertTrue(Notification.objects.filter(verb="NEW_ORG_REGISTRATION", recipient=garant).exists())

    @patch("users.services.fetch_ares_data")
    def test_register_organization_persists_legal_form(self, mock_fetch_ares):
        """legal_form (z pravniForma) se uloží do EmployerProfile."""
        mock_fetch_ares.return_value = EkonomickySubjektDTO(
            ico="12345678",
            obchodniJmeno="ARES Corp",
            sidlo=Adresa(textovaAdresa="Test Address", psc=12345),
            dic="CZ12345678",
            pravniForma="Akciová společnost",
        )

        user = register_organization(self.valid_register_data)

        self.assertEqual(user.employer_profile.legal_form, "Akciová společnost")
        self.assertFalse(user.employer_profile.manual_ares_entry)
        self.assertTrue(user.employer_profile.ares_locked)

    @patch("users.services.fetch_ares_data")
    @patch("users.services.transaction.on_commit")
    def test_register_organization_manual_override_notifies_garants(self, mock_on_commit, mock_fetch_ares):
        """Ruční přepis ARES dat → varování garantům (bez ARES výpadku)."""
        _execute_on_commit(mock_on_commit)
        mock_fetch_ares.return_value = EkonomickySubjektDTO(
            ico="12345678",
            obchodniJmeno="ARES Corp",
            sidlo=Adresa(textovaAdresa="ARES Address", psc=12345),
            dic="CZ12345678",
        )
        garant = self._create_garant()

        register_organization(self.valid_register_data)  # companyName "Test Corp" ≠ "ARES Corp"

        self.assertTrue(Notification.objects.filter(verb="MANUAL_REGISTRATION", recipient=garant).exists())

    @patch("users.services.fetch_ares_data")
    def test_update_organization_from_ares_outage_raises_value_error(self, mock_fetch_ares):
        """AresUnavailableError v update_organization_from_ares → ValueError (zachování 400)."""
        user = OrganizationUser.objects.create(email="update@test.com", first_name="U", last_name="D")
        mock_fetch_ares.side_effect = AresUnavailableError("ARES down")

        with self.assertRaises(ValueError):
            update_organization_from_ares(user, "87654321")

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
        user.refresh_from_db()
        profile = user.employer_profile
        self.assertIsNotNone(profile)
        self.assertEqual(profile.ico, "87654321")
        self.assertEqual(profile.company_name, "Updated Corp")
        self.assertEqual(profile.address, "New Address 1")
