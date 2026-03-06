from django.test import TestCase

from users.models import OrganizationUser, StudentUser
from users.serializers import (
    AresJusticeSerializer,
    ChangePasswordSerializer,
    OrganizationRegisterSerializer,
    PasswordResetConfirmSerializer,
    UserInfoSerializer,
)

# ===========================================================================
# OrganizationRegisterSerializer — ICO validation and password matching
# ===========================================================================


class OrganizationRegisterSerializerTests(TestCase):
    _BASE = {
        "email": "org@example.com",
        "phone": "123456789",
        "password": "StrongPass123!",
        "password2": "StrongPass123!",
        "first_name": "Jan",
        "last_name": "Novák",
    }

    def _data(self, **overrides):
        return {**self._BASE, **overrides}

    # --- ICO validation ---------------------------------------------------

    def test_valid_ico_exactly_8_digits(self):
        s = OrganizationRegisterSerializer(data=self._data(ico="12345678"))
        # ico itself is valid; other errors (e.g. ARES) are separate
        s.is_valid()
        self.assertNotIn("ico", s.errors)

    def test_invalid_ico_7_digits(self):
        s = OrganizationRegisterSerializer(data=self._data(ico="1234567"))
        s.is_valid()
        self.assertIn("ico", s.errors)

    def test_invalid_ico_9_digits(self):
        s = OrganizationRegisterSerializer(data=self._data(ico="123456789"))
        s.is_valid()
        self.assertIn("ico", s.errors)

    def test_invalid_ico_contains_letters(self):
        s = OrganizationRegisterSerializer(data=self._data(ico="1234567A"))
        s.is_valid()
        self.assertIn("ico", s.errors)

    def test_invalid_ico_empty(self):
        s = OrganizationRegisterSerializer(data=self._data(ico=""))
        s.is_valid()
        self.assertIn("ico", s.errors)

    # --- Password matching ------------------------------------------------

    def test_password_mismatch_raises_error(self):
        s = OrganizationRegisterSerializer(data=self._data(ico="12345678", password="StrongPass123!", password2="Different1!"))
        s.is_valid()
        self.assertIn("password", s.errors)

    # --- Required fields --------------------------------------------------

    def test_missing_email_raises_error(self):
        data = self._data(ico="12345678")
        del data["email"]
        s = OrganizationRegisterSerializer(data=data)
        s.is_valid()
        self.assertIn("email", s.errors)

    def test_missing_first_name_raises_error(self):
        data = self._data(ico="12345678")
        del data["first_name"]
        s = OrganizationRegisterSerializer(data=data)
        s.is_valid()
        self.assertIn("first_name", s.errors)


# ===========================================================================
# ChangePasswordSerializer
# ===========================================================================


class ChangePasswordSerializerTests(TestCase):
    def test_valid_data_passes(self):
        s = ChangePasswordSerializer(
            data={
                "old_password": "OldPass123!",
                "new_password": "NewStrongPass1!",
                "new_password_confirm": "NewStrongPass1!",
            }
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_mismatched_new_passwords(self):
        s = ChangePasswordSerializer(
            data={
                "old_password": "OldPass123!",
                "new_password": "NewStrongPass1!",
                "new_password_confirm": "DifferentPass1!",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("new_password_confirm", s.errors)

    def test_weak_new_password_rejected(self):
        s = ChangePasswordSerializer(
            data={
                "old_password": "OldPass123!",
                "new_password": "123",
                "new_password_confirm": "123",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("new_password", s.errors)

    def test_missing_old_password(self):
        s = ChangePasswordSerializer(
            data={
                "new_password": "NewStrongPass1!",
                "new_password_confirm": "NewStrongPass1!",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("old_password", s.errors)


# ===========================================================================
# PasswordResetConfirmSerializer
# ===========================================================================


class PasswordResetConfirmSerializerTests(TestCase):
    def test_valid_data_passes(self):
        s = PasswordResetConfirmSerializer(
            data={
                "uidb64": "abc123",
                "token": "some-token",
                "new_password": "NewStrongPass1!",
                "new_password_confirm": "NewStrongPass1!",
            }
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_mismatched_passwords_rejected(self):
        s = PasswordResetConfirmSerializer(
            data={
                "uidb64": "abc123",
                "token": "some-token",
                "new_password": "NewStrongPass1!",
                "new_password_confirm": "DifferentPass1!",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("new_password_confirm", s.errors)

    def test_weak_password_rejected(self):
        s = PasswordResetConfirmSerializer(
            data={
                "uidb64": "abc123",
                "token": "some-token",
                "new_password": "abc",
                "new_password_confirm": "abc",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("new_password", s.errors)


# ===========================================================================
# AresJusticeSerializer — ICO RegexField
# ===========================================================================


class AresJusticeSerializerTests(TestCase):
    def test_valid_8_digit_ico(self):
        s = AresJusticeSerializer(data={"ico": "12345678"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_7_digit_ico(self):
        s = AresJusticeSerializer(data={"ico": "1234567"})
        self.assertFalse(s.is_valid())
        self.assertIn("ico", s.errors)

    def test_invalid_9_digit_ico(self):
        s = AresJusticeSerializer(data={"ico": "123456789"})
        self.assertFalse(s.is_valid())
        self.assertIn("ico", s.errors)

    def test_invalid_letters_in_ico(self):
        s = AresJusticeSerializer(data={"ico": "1234567A"})
        self.assertFalse(s.is_valid())
        self.assertIn("ico", s.errors)

    def test_invalid_empty_ico(self):
        s = AresJusticeSerializer(data={"ico": ""})
        self.assertFalse(s.is_valid())
        self.assertIn("ico", s.errors)


# ===========================================================================
# UserInfoSerializer — role serialization
# ===========================================================================


class UserInfoSerializerTests(TestCase):
    def test_superuser_gets_admin_role(self):
        admin = OrganizationUser.objects.create(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
        )
        data = UserInfoSerializer(admin).data
        self.assertEqual(data["role"], "admin")

    def test_student_role_always_gets_st_role(self):
        student = StudentUser.objects.create(
            email="student@example.com",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )
        data = UserInfoSerializer(student).data
        # StudentUser now always returns "ST" as role
        self.assertEqual(data["role"], "ST")

    def test_favorite_practices_empty_list_for_new_student(self):
        student = StudentUser.objects.create(
            email="student2@example.com",
            first_name="Jana",
            last_name="Novák",
            is_active=True,
        )
        data = UserInfoSerializer(student).data
        self.assertEqual(data["favorite_practices"], [])

    def test_email_and_name_fields_present(self):
        user = OrganizationUser.objects.create(
            email="check@example.com",
            first_name="Petr",
            last_name="Novák",
            is_active=True,
        )
        data = UserInfoSerializer(user).data
        self.assertEqual(data["email"], "check@example.com")
        self.assertEqual(data["firstName"], "Petr")
        self.assertEqual(data["lastName"], "Novák")
