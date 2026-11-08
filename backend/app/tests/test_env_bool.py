"""A-20 — jednotné parsování boolean proměnných prostředí; produkční pojistky zůstávají v platnosti."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from app.settings import env_bool

BACKEND = Path(__file__).resolve().parents[2]


class EnvBoolTests(SimpleTestCase):
    def test_truthy_and_falsy_values(self):
        for value in ("1", "true", "True", "TRUE", "yes", "on", " 1 "):
            with (
                self.subTest(value=value),
                mock.patch.dict(os.environ, {"X_FLAG": value}),
            ):
                self.assertTrue(env_bool("X_FLAG"))
        for value in ("0", "false", "False", "no", "off", "", "2", "nonsense"):
            with (
                self.subTest(value=value),
                mock.patch.dict(os.environ, {"X_FLAG": value}),
            ):
                self.assertFalse(env_bool("X_FLAG"))

    def test_unset_uses_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("X_UNSET", None)
            self.assertFalse(env_bool("X_UNSET"))
            self.assertTrue(env_bool("X_UNSET", True))


class ProductionGuardsTests(SimpleTestCase):
    """Pojistky z settings.py (STAG_MOCK, DEMO_LOGIN, '*' v ALLOWED_HOSTS) platí pro všechny podoby 'pravdy'."""

    def _import_settings(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("DEBUG", "STAG_MOCK", "DEMO_LOGIN", "ALLOWED_HOSTS")}
        env.update(
            {
                "DJANGO_SECRET_KEY": "x" * 40,
                # Platný Fernet klíč (32 nulových bajtů) — produkce ho vyžaduje.
                "STAG_TICKET_ENCRYPTION_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.org",
                **extra,
            }
        )
        return subprocess.run(
            [sys.executable, "-c", "import app.settings"],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_secure_configuration_starts(self):
        self.assertEqual(self._import_settings().returncode, 0)

    def test_missing_stag_ticket_encryption_key_blocked(self):
        result = self._import_settings(STAG_TICKET_ENCRYPTION_KEY="")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STAG_TICKET_ENCRYPTION_KEY", result.stderr)

    def test_invalid_stag_ticket_encryption_key_blocked(self):
        result = self._import_settings(STAG_TICKET_ENCRYPTION_KEY="not-a-fernet-key")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STAG_TICKET_ENCRYPTION_KEY", result.stderr)

    def test_stag_mock_and_demo_login_blocked_in_any_truthy_form(self):
        for name in ("STAG_MOCK", "DEMO_LOGIN"):
            for value in ("1", "True", "true", "yes"):
                with self.subTest(name=name, value=value):
                    result = self._import_settings(**{name: value})
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("SECURITY ERROR", result.stderr)

    def test_wildcard_allowed_hosts_blocked(self):
        self.assertEqual(self._import_settings(ALLOWED_HOSTS="*").returncode, 1)
