from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from api.models import SystemParameter
from api.parameter_service import get_param


class SystemParameterTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_falls_back_to_settings_value(self):
        self.assertEqual(get_param("PRACTICE_CREDIT_ALERT_DAYS", 14), 14)

    def test_database_override_is_used(self):
        SystemParameter.objects.create(key="PRACTICE_CREDIT_ALERT_DAYS", value=21)
        self.assertEqual(get_param("PRACTICE_CREDIT_ALERT_DAYS", 14), 21)

    def test_invalid_database_value_falls_back(self):
        SystemParameter.objects.create(key="PRACTICE_CREDIT_ALERT_DAYS", value="21")
        with self.assertLogs("api.parameter_service", level="WARNING"):
            self.assertEqual(get_param("PRACTICE_CREDIT_ALERT_DAYS", 14), 14)

    def test_save_and_delete_invalidate_cache(self):
        parameter = SystemParameter.objects.create(key="PRACTICE_CREDIT_ALERT_DAYS", value=21)
        self.assertEqual(get_param(parameter.key, 14), 21)
        parameter.value = 28
        parameter.save()
        self.assertEqual(get_param(parameter.key, 14), 28)
        parameter.delete()
        self.assertEqual(get_param(parameter.key, 14), 14)

    @patch("student_practices.management.commands.notify_practice_deadlines.Command._notify_start_urgent")
    @patch("student_practices.management.commands.notify_practice_deadlines.Command._notify_credit_alert")
    def test_deadline_command_uses_database_override(self, credit_alert, urgency):
        SystemParameter.objects.create(key="PRACTICE_URGENCY_DAYS", value=[10, 5])
        SystemParameter.objects.create(key="PRACTICE_CREDIT_ALERT_DAYS", value=30)
        from student_practices.management.commands.notify_practice_deadlines import Command

        Command().handle()
        urgency.assert_called_once()
        self.assertEqual(urgency.call_args.args[1], [10, 5])
        credit_alert.assert_called_once_with(30)
