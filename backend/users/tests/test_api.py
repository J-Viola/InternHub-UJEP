# Create your tests here.
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from users.serializers import CustomTokenObtainPairSerializer, LogoutSerializer, OrganizationRegisterSerializer
from users.views import AresJusticeView

User = get_user_model()


class CustomTokenObtainPairSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="StrongPassword123",
            is_active=True,
        )
        self.serializer = CustomTokenObtainPairSerializer()

    @patch("requests.get")
    def authenticatesWithValidStagTicket(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "student@example.com"}
        mock_get.return_value = mock_response

        attrs = {"service_ticket": "valid-ticket"}
        result = self.serializer.validate(attrs)

        self.assertIn("refresh", result)
        self.assertIn("access", result)
        user = User.objects.get(email="student@example.com")
        self.assertTrue(user.is_active)

    @patch("requests.get")
    def failsWithInvalidStagTicket(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        attrs = {"service_ticket": "invalid-ticket"}
        with self.assertRaises(Exception) as context:
            self.serializer.validate(attrs)
        self.assertIn("Failed to authenticate with STAG", str(context.exception))

    def authenticatesWithValidCredentials(self):
        attrs = {"email": "test@example.com", "password": "StrongPassword123"}
        result = self.serializer.validate(attrs)

        self.assertIn("refresh", result)
        self.assertIn("access", result)

    def failsWithInvalidPassword(self):
        attrs = {"email": "test@example.com", "password": "WrongPassword"}
        with self.assertRaises(Exception) as context:
            self.serializer.validate(attrs)
        self.assertIn("Invalid credentials", str(context.exception))

    def failsWithNonExistentEmail(self):
        attrs = {
            "email": "nonexistent@example.com",
            "password": "StrongPassword123",
        }
        with self.assertRaises(Exception) as context:
            self.serializer.validate(attrs)
        self.assertIn("No account found", str(context.exception))

    def requiresCredentials(self):
        attrs = {}
        with self.assertRaises(Exception) as context:
            self.serializer.validate(attrs)
        self.assertIn("Email and password are required", str(context.exception))


class RegisterSerializerTests(TestCase):
    def registerWithValidData(self):
        data = {
            "email": "new@example.com",
            "password": "StrongPassword123",
            "password2": "StrongPassword123",
            "first_name": "John",
            "last_name": "Doe",
        }
        serializer = OrganizationRegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("StrongPassword123"))

    def failsWithMismatchedPasswords(self):
        data = {
            "email": "new@example.com",
            "password": "StrongPassword123",
            "password2": "DifferentPassword",
            "first_name": "John",
            "last_name": "Doe",
        }
        serializer = OrganizationRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
        self.assertIn("didn't match", str(serializer.errors["password"]))

    def failsWithMissingRequiredFields(self):
        data = {
            "email": "new@example.com",
            "password": "StrongPassword123",
            "password2": "StrongPassword123",
        }
        serializer = OrganizationRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name", serializer.errors)
        self.assertIn("last_name", serializer.errors)


class LogoutSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="StrongPassword123",
        )
        self.refresh_token = RefreshToken.for_user(self.user)

    def serializesValidToken(self):
        data = {"refresh": str(self.refresh_token)}
        serializer = LogoutSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["refresh"], str(self.refresh_token))


class RegisterViewTests(APITestCase):
    def registersUserSuccessfully(self):
        url = reverse("register")
        data = {
            "email": "new@example.com",
            "password": "StrongPassword123",
            "password2": "StrongPassword123",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, "new@example.com")


class LogoutViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="StrongPassword123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.refresh_token = RefreshToken.for_user(self.user)

    def successfullyLogsOut(self):
        url = reverse("logout")
        data = {"refresh": str(self.refresh_token)}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["success"], "Successfully logged out")


class AresViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="StrongPassword123",
        )

    @patch("requests.get")
    def fetchesValidAresData(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ico": "12345678",
            "name": "Test Company",
        }
        mock_get.return_value = mock_response

        request = self.factory.get("/ares/?ico=12345678")
        request.user = self.user
        view = AresJusticeView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["ico"], "12345678")

    def returnsBadRequestForMissingIco(self):
        request = self.factory.get("/ares/")
        request.user = self.user
        view = AresJusticeView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("missing", data["error"])

    def returnsBadRequestForInvalidIcoFormat(self):
        request = self.factory.get("/ares/?ico=1234")
        request.user = self.user
        view = AresJusticeView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Invalid IČO format", data["error"])

    @patch("users.views.cache")
    @patch("requests.get")
    def usesCachedDataWhenAvailable(self, mock_get, mock_cache):
        cached_data = {"ico": "12345678", "name": "Cached Company"}
        mock_cache.get.return_value = cached_data

        request = self.factory.get("/ares/?ico=12345678")
        request.user = self.user
        view = AresJusticeView.as_view()
        response = view(request)

        self.assertEqual(data, cached_data)
        mock_get.assert_not_called()


class UserProfileTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        from api.models import EmployerProfile, OrganizationRole, OrganizationUser, StudentUser

        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )

        self.org_user = OrganizationUser.objects.create(
            email="org@test.com",
            first_name="Org",
            last_name="Boss",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.profile

    def test_current_profile_student(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("users:current_user_profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_type"], "student")
        self.assertIn("os_cislo", response.data)

    def test_current_profile_organization(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.get(reverse("users:current_user_profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_type"], "organization")
        self.assertIn("employer_profile", response.data)
        self.assertEqual(response.data["employer_profile"]["company_name"], "Test Co")


class OrganizationUserListTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        from api.models import ApprovalStatus, EmployerProfile, OrganizationUser

        self.owner = OrganizationUser.objects.create(email="owner@test.com", is_active=True)
        self.profile = EmployerProfile.objects.create(
            employer_id=self.owner.id,
            company_name="My Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.owner.employer_profile = self.profile

        self.employee = OrganizationUser.objects.create(email="emp@test.com", is_active=True)
        self.employee.employer_profile = self.profile
        self.employee.save()

        self.other = OrganizationUser.objects.create(email="other@test.com", is_active=True)  # No profile

    def test_list_users_in_organization(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse("users:organization_users"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see owner and employee
        ids = [u["id"] for u in response.data]
        self.assertIn(self.owner.id, ids)
        self.assertIn(self.employee.id, ids)
        self.assertNotIn(self.other.id, ids)
