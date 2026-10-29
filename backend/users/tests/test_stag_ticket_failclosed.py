"""A-10 — STAG ticket: neplatný podpis vede k odmítnutí, STAG klient se nevolá."""

import importlib
from unittest import mock

from django.apps import apps
from django.test import TestCase, override_settings

from users.models import InvalidStagTicketError, StagUser, StudentUser
from users.services import fetch_student_data_from_stag


@override_settings(STAG_MOCK=False, DEMO_LOGIN=False)
class StagTicketFailClosedTests(TestCase):
    def setUp(self):
        self.student = StudentUser.objects.create(email="a10@test.local", os_cislo="A10", is_active=True)

    def _set_raw_ticket(self, value):
        StagUser.objects.filter(pk=self.student.pk).update(stag_ticket=value)
        return StudentUser.objects.get(pk=self.student.pk)

    def test_valid_signed_ticket_works_unchanged(self):
        self.student.stag_ticket = "abc123"
        self.student.save()
        student = StudentUser.objects.get(pk=self.student.pk)
        self.assertNotEqual(student.stag_ticket, "abc123")  # uloženo podepsané
        self.assertEqual(student.get_ticket(), "abc123")
        with mock.patch("users.services.get_stag_client") as client:
            client.return_value.get_student_info.return_value = {}
            fetch_student_data_from_stag(student)
        client.return_value.get_student_info.assert_called_once_with("abc123", "A10")

    def test_tampered_ticket_is_rejected_and_stag_not_called(self):
        self.student.stag_ticket = "abc123"
        self.student.save()
        student = StudentUser.objects.get(pk=self.student.pk)
        tampered = student.stag_ticket.replace("abc123", "evil99", 1)
        student = self._set_raw_ticket(tampered)
        with mock.patch("users.services.get_stag_client") as client:
            with self.assertLogs("users.services", level="WARNING") as logs:
                with self.assertRaises(InvalidStagTicketError):
                    fetch_student_data_from_stag(student)
        client.return_value.get_student_info.assert_not_called()
        self.assertNotIn("evil99", "".join(logs.output))

    def test_regular_save_does_not_resign_corrupted_ticket(self):
        """Běžné save() načteného uživatele nesmí poškozený ticket „legitimizovat"."""
        student = self._set_raw_ticket("plaintext-ticket")
        student.first_name = "Změna"
        student.save()
        student = StudentUser.objects.get(pk=self.student.pk)
        self.assertEqual(student.stag_ticket, "plaintext-ticket")
        with self.assertRaises(InvalidStagTicketError):
            student.get_ticket()

    def test_generate_contract_propagates_invalid_ticket(self):
        """A-10: generate_contract() neplatný ticket nespolkne ani neoznačí fetch za úspěšný."""
        from student_practices import services as sp_services
        from student_practices.models import StudentPractice

        student = self._set_raw_ticket("plaintext-ticket")
        sp = StudentPractice(user=student)
        sp_services._stag_data_cache.pop("A10", None)
        with mock.patch("users.services.get_stag_client") as client:
            with self.assertRaises(InvalidStagTicketError):
                sp_services.generate_contract(sp)
        client.return_value.get_student_info.assert_not_called()
        self.assertNotIn("A10", sp_services._stag_data_cache)

    def test_plaintext_ticket_is_rejected(self):
        student = self._set_raw_ticket("plaintext-ticket")
        with mock.patch("users.services.get_stag_client") as client:
            with self.assertRaises(InvalidStagTicketError):
                fetch_student_data_from_stag(student)
        client.return_value.get_student_info.assert_not_called()
        with self.assertRaises(InvalidStagTicketError):
            student.get_ticket()

    def test_migration_clears_unsigned_and_keeps_signed(self):
        self.student.stag_ticket = "keepme"
        self.student.save()
        other = StudentUser.objects.create(email="a10b@test.local", os_cislo="A10B", is_active=True)
        StagUser.objects.filter(pk=other.pk).update(stag_ticket="plaintext")
        migration = importlib.import_module("users.migrations.0018_sign_or_clear_stag_tickets")
        migration.clear_unsigned_tickets(apps, None)
        self.assertEqual(StudentUser.objects.get(pk=other.pk).stag_ticket, "")
        self.assertEqual(
            StudentUser.objects.get(pk=self.student.pk).get_ticket(),
            "keepme",
        )
