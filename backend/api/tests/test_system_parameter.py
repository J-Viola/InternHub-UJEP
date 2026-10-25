"""A-26 — SystemSettings (django-solo singleton) nahrazuje obecný klíč–hodnota SystemParameter."""

from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings

from api.admin import SystemSettingsAdmin
from api.models import SystemSettings
from users.models import ActionLog

LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "a26",
    }
}


class SystemSettingsTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_defaults_on_empty_db(self):
        s = SystemSettings.get_solo()
        self.assertEqual(s.practice_urgency_days, [14, 7, 2])
        self.assertEqual(s.practice_credit_alert_days, 14)
        self.assertEqual(s.practice_contract_overdue_days, 7)
        self.assertEqual(s.practice_approval_stall_days, 7)
        self.assertEqual(s.max_upload_size, 10 * 1024 * 1024)

    def test_invalid_values_rejected_by_full_clean(self):
        cases = [
            ("practice_credit_alert_days", 0),
            ("practice_credit_alert_days", 366),
            ("practice_contract_overdue_days", 0),
            ("practice_approval_stall_days", 366),
            ("max_upload_size", 0),
            ("max_upload_size", 21 * 1024 * 1024),
            ("practice_urgency_days", []),
            ("practice_urgency_days", [7, 7]),
            ("practice_urgency_days", [2, 7]),
            ("practice_urgency_days", ["7"]),
            ("practice_urgency_days", [-1]),
            ("practice_urgency_days", [True]),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                s = SystemSettings.get_solo()
                setattr(s, field, value)
                with self.assertRaises(ValidationError):
                    s.full_clean()

    def test_save_validates_outside_admin(self):
        s = SystemSettings.get_solo()
        s.max_upload_size = 0
        with self.assertRaises(ValidationError):
            s.save()

    @override_settings(CACHES=LOCMEM)
    def test_change_is_visible_through_shared_cache(self):
        s = SystemSettings.get_solo()
        s.practice_credit_alert_days = 30
        s.save()
        self.assertEqual(SystemSettings.get_solo().practice_credit_alert_days, 30)

    @patch("student_practices.management.commands.notify_practice_deadlines.Command._notify_start_urgent")
    @patch("student_practices.management.commands.notify_practice_deadlines.Command._notify_credit_alert")
    def test_deadline_command_uses_settings(self, credit_alert, urgency):
        s = SystemSettings.get_solo()
        s.practice_urgency_days = [10, 5]
        s.practice_credit_alert_days = 30
        s.save()
        from student_practices.management.commands.notify_practice_deadlines import (
            Command,
        )

        Command().handle()
        urgency.assert_called_once()
        self.assertEqual(urgency.call_args.args[1], [10, 5])
        credit_alert.assert_called_once_with(30)


class SystemSettingsAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_superuser(email="a26@test.local", password="x")
        self.model_admin = SystemSettingsAdmin(SystemSettings, admin.site)
        self.request = RequestFactory().post("/")
        self.request.user = self.admin

    def test_cannot_add_second_or_delete(self):
        SystemSettings.get_solo()
        self.assertFalse(self.model_admin.has_add_permission(self.request))
        self.assertFalse(self.model_admin.has_delete_permission(self.request))

    def test_change_writes_action_log_with_old_and_new_value(self):
        obj = SystemSettings.get_solo()
        form_cls = self.model_admin.get_form(self.request, obj)
        data = {
            "practice_urgency_days": "[14, 7, 2]",
            "practice_credit_alert_days": 21,
            "practice_contract_overdue_days": 7,
            "practice_approval_stall_days": 7,
            "max_upload_size": 10 * 1024 * 1024,
        }
        form = form_cls(data, instance=obj)
        self.assertTrue(form.is_valid(), form.errors)
        self.model_admin.save_model(self.request, form.save(commit=False), form, True)
        log = ActionLog.objects.get(action_type="SYSTEM_SETTINGS_CHANGED")
        self.assertIn("practice_credit_alert_days: 14 → 21", log.action_description)
