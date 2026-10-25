"""BL-07 — testy izolačních gard (DB identity, flush/reset, ARES, e-mail).

Uzavírá gap list z ``audit/2026-10-04/lanes/bl07-sandbox-proof.md``:
(1) runtime DB-identity guard, (3) reset/flush jde přes tento guard,
(2) ARES mock guard jako STAG, (4) locmem e-mail vynucený nastavením.

Soubor je NOVÝ — žádný legacy test (test_phase2, test_wp08_capacity,
test_phase4, wp10/wp13, practices apply-capacity) se nemění.
"""

import ast
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import get_commands
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

from app.db_identity import (
    NonDisposableDatabaseError,
    assert_disposable_db,
    assert_runner_db_identities,
    assert_runner_db_identity,
    is_disposable_db_name,
    runner_db_name,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _flush_call_lines(tree):
    call_command_names = set()
    management_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "django.core.management":
            call_command_names.update(alias.asname or alias.name for alias in node.names if alias.name == "call_command")
        elif isinstance(node, ast.ImportFrom) and node.module == "django.core":
            management_names.update(alias.asname or alias.name for alias in node.names if alias.name == "management")
        elif isinstance(node, ast.Import):
            management_names.update(alias.asname or "management" for alias in node.names if alias.name == "django.core.management")

    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value != "flush":
            continue
        func = node.func
        is_call_command = (isinstance(func, ast.Name) and func.id in call_command_names) or (
            isinstance(func, ast.Attribute)
            and func.attr == "call_command"
            and isinstance(func.value, ast.Name)
            and func.value.id in management_names
        )
        if is_call_command:
            lines.append(node.lineno)
    return lines


class DbIdentitySchemeTests(TestCase):
    """Schématu disposable jmen (BL-07 dossier §1.1, Gate 1)."""

    def test_proven_mappings_are_disposable(self):
        # host / Docker (.env PG_DB=internhub) / CI — viz dossier §1.2
        for configured, derived in [
            ("test_internhub", "test_test_internhub"),
            ("internhub", "test_internhub"),
            ("internhub_test", "test_internhub_test"),
            ("bl07_test_20261008_1200", "test_bl07_test_20261008_1200"),
        ]:
            cfg = {"ENGINE": "django.db.backends.postgresql", "NAME": configured}
            self.assertEqual(runner_db_name(cfg), derived)
            self.assertEqual(assert_runner_db_identity(cfg), derived)
            self.assertTrue(is_disposable_db_name(derived))
            self.assertTrue(is_disposable_db_name(configured) or configured == "internhub")

    def test_non_test_names_are_not_disposable(self):
        engine = "django.db.backends.postgresql"
        for name in ["internhub", "internhub_prod", "prod", "databaze", ""]:
            self.assertFalse(is_disposable_db_name(name, engine), name)

    def test_in_memory_sqlite_is_disposable(self):
        self.assertTrue(is_disposable_db_name(":memory:", "django.db.backends.sqlite3"))

    def test_runner_refuses_non_disposable_target(self):
        # TEST.NAME explicitně na nedisposable jméno → runner by směřoval mimo schéma
        cfg = {"ENGINE": "django.db.backends.postgresql", "NAME": "internhub", "TEST": {"NAME": "internhub"}}
        with self.assertRaises(ImproperlyConfigured):
            assert_runner_db_identity(cfg)

    def test_runner_refuses_direct_operation_on_configured_db(self):
        # TEST.NAME == NAME (i když obsahuje "test") → žádná izolace runneru
        cfg = {"ENGINE": "django.db.backends.postgresql", "NAME": "internhub_test", "TEST": {"NAME": "internhub_test"}}
        with self.assertRaises(ImproperlyConfigured):
            assert_runner_db_identity(cfg)

    def test_runner_refuses_empty_configured_name(self):
        with self.assertRaises(ImproperlyConfigured):
            assert_runner_db_identity({"ENGINE": "django.db.backends.postgresql", "NAME": ""})

    def test_runner_allows_in_memory_sqlite_pair(self):
        cfg = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "TEST": {"NAME": ":memory:"}}
        self.assertEqual(assert_runner_db_identity(cfg), ":memory:")

    def test_runner_rejects_shared_file_test_name_even_when_configured_name_is_memory(self):
        cfg = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "TEST": {"NAME": "/tmp/shared.sqlite3"},
        }
        with self.assertRaises(ImproperlyConfigured):
            assert_runner_db_identity(cfg)

    def test_runner_checks_every_database_alias(self):
        good = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        bad = {"ENGINE": "django.db.backends.postgresql", "NAME": "internhub", "TEST": {"NAME": "internhub"}}
        self.assertEqual(assert_runner_db_identities({"default": good}), {"default": ":memory:"})
        with self.assertRaises(ImproperlyConfigured):
            assert_runner_db_identities({"default": good, "other": bad})

    def test_effective_session_config_is_disposable(self):
        # Gate 2c podle nastavení, kterým běží tato session.
        cfg = settings.DATABASES["default"]
        target = assert_runner_db_identity(cfg, operation="session")
        self.assertTrue(is_disposable_db_name(target, str(cfg.get("ENGINE") or "")))


class SettingsCheckTests(TestCase):
    """Gap #1 — settings check sám odmítne ne-disposable konfiguraci (fail-closed)."""

    def _run_django_setup(self, pg_db: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "app.test_settings", "PG_DB": pg_db}
        env.pop("ALLOW_LIVE_EXTERNAL", None)
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_test_settings_refuses_non_test_pg_db(self):
        # PG_DB="" → jméno chybí → načtení nastavení SELŽE (nic se nespustí).
        proc = self._run_django_setup("")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("BL-07 guard", proc.stderr)

    def test_test_settings_loads_with_test_pg_db(self):
        proc = self._run_django_setup("test_internhub")
        self.assertEqual(proc.returncode, 0, proc.stderr)


class FlushCommandGuardTests(TestCase):
    """Reset boundary lives in E2E support; Django's regular command is restored."""

    def test_flush_command_is_django_core_command(self):
        self.assertEqual(get_commands()["flush"], "django.core")

    @override_settings(DEBUG=False, DB_IDENTITY_GUARD=None)
    def test_guard_is_inactive_in_production_config(self):
        # Produkce (DEBUG=False) → guard nečinný, provozní chování se nemění.
        with mock.patch.dict(connection.settings_dict, {"NAME": "internhub"}):
            assert_disposable_db("flush")  # bez výjimky

    @mock.patch.dict(os.environ, {"BL07_ALLOW_NON_TEST_DB": "1"})
    def test_explicit_operator_opt_in_allows_non_test_db(self):
        with mock.patch.dict(connection.settings_dict, {"NAME": "internhub"}):
            assert_disposable_db("flush")  # bez výjimky (vědomý lidský opt-in)


class ResetEndpointGuardTests(TestCase):
    """Gap #3 — E2E reset endpoint končí na téže gardě (end-to-end)."""

    URL = "/api/test/reset-db/"

    @staticmethod
    def _call_reset_view():
        # Volání view přímo (mimo URL routing) → deterministické bez ohledu na
        # pořadí načtení urlpři DEBUG.
        from django.test import RequestFactory

        from api.views import TestResetDBView

        request = RequestFactory().post("/api/test/reset-db/")
        return TestResetDBView.as_view()(request)

    @override_settings(DEBUG=True)
    def test_reset_refused_on_non_disposable_db_without_flushing(self):
        from department.models import Department

        marker = Department.objects.create(department_name="BL07 reset marker", department_code="B7R")

        with (
            mock.patch.dict(connection.settings_dict, {"NAME": "internhub_prod"}),
            mock.patch("test_support.db_reset.call_command") as flush,
            mock.patch("django.core.management.call_command") as seed,
        ):
            response = self._call_reset_view()

        self.assertEqual(response.status_code, 500)
        detail = str(json.loads(response.content).get("detail", ""))
        self.assertIn("non-disposable database", detail)
        # Endpoint se dostal až k guardu → žádný flush/seed proběhl.
        self.assertTrue(Department.objects.filter(pk=marker.pk).exists())
        flush.assert_not_called()
        seed.assert_not_called()

    @override_settings(DEBUG=False)
    def test_reset_refused_outside_debug_preserves_audit_classification(self):
        # TEST_RESULTS.md:27 a dossier Gate 5a — mimo DEBUG odmítnuto ještě
        # před guardem (403); klientské volání proto není produkční exploit.
        response = self._call_reset_view()
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True, STAG_MOCK=False)
    def test_reset_refuses_when_stag_is_real(self):
        with mock.patch("test_support.db_reset.reset_e2e_database") as reset:
            response = self._call_reset_view()
        self.assertEqual(response.status_code, 400)
        reset.assert_not_called()

    def test_production_urlconf_omits_test_endpoints(self):
        import importlib

        from django.urls import Resolver404, clear_url_caches, resolve

        import app.urls
        from app import settings as app_settings

        with mock.patch.object(app_settings, "DEBUG", False):
            importlib.reload(app.urls)
            clear_url_caches()
            for url in (self.URL, "/api/test/scenario/student-has-applications/"):
                with self.subTest(url=url), self.assertRaises(Resolver404):
                    resolve(url)
        importlib.reload(app.urls)
        clear_url_caches()

    def test_reset_has_no_direct_project_flush_callsite(self):
        backend = BACKEND_DIR
        allowed = {"test_support/db_reset.py"}
        for path in backend.rglob("*.py"):
            rel = path.relative_to(backend).as_posix()
            if rel.startswith(("app/tests/",)) or "/tests/" in rel or rel.endswith("_test.py"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            for line in _flush_call_lines(tree):
                self.assertIn(rel, allowed, f"unapproved flush callsite: {rel}:{line}")

    def test_ast_flush_guard_detects_direct_call_command_import(self):
        tree = ast.parse('from django.core.management import call_command\ncall_command("flush")')
        self.assertEqual(_flush_call_lines(tree), [2])

    @override_settings(DEBUG=False, DB_IDENTITY_GUARD=False, E2E_RESET_ENABLED=True)
    @mock.patch.dict(os.environ, {"BL07_ALLOW_NON_TEST_DB": "1"})
    def test_service_check_cannot_be_bypassed_by_debug_guard_or_env(self):
        with (
            mock.patch.dict(connection.settings_dict, {"NAME": "internhub_prod"}),
            mock.patch("test_support.db_reset.call_command") as flush,
        ):
            from test_support.db_reset import reset_e2e_database

            with self.assertRaises(NonDisposableDatabaseError):
                reset_e2e_database()
        flush.assert_not_called()

    @override_settings(E2E_RESET_ENABLED=False)
    def test_service_requires_explicit_test_context(self):
        from test_support.db_reset import reset_e2e_database

        with self.assertRaises(NonDisposableDatabaseError):
            reset_e2e_database()

    @override_settings(E2E_RESET_ENABLED=True)
    def test_service_passes_requested_alias_to_django_flush(self):
        from test_support.db_reset import reset_e2e_database

        alias = "isolated"
        config = {**connection.settings_dict, "NAME": "unit_test_db"}
        with (
            mock.patch.dict("test_support.db_reset.connections.databases", {alias: config}),
            mock.patch("test_support.db_reset.call_command") as flush,
        ):
            reset_e2e_database(using=alias)
        flush.assert_called_once()
        self.assertEqual(flush.call_args.args[0].__class__.__module__, "django.core.management.commands.flush")
        self.assertEqual(flush.call_args.kwargs, {"database": alias, "interactive": False})


@override_settings(E2E_RESET_ENABLED=True)
class E2EDatabaseResetIntegrationTests(TransactionTestCase):
    """Exercise the real built-in flush on the isolated in-memory runner DB."""

    def test_reset_removes_marker_from_effective_database(self):
        from test_support.db_reset import reset_e2e_database

        from department.models import Department

        marker = Department.objects.create(department_name="E2E reset marker", department_code="ER1")
        reset_e2e_database(using="default")
        self.assertFalse(Department.objects.filter(pk=marker.pk).exists())


class AresMockGuardTests(TestCase):
    """Gap #2 — ARES bez odchozího HTTP, pokud není výslovný opt-in."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_test_context_forces_ares_mock(self):
        self.assertTrue(settings.ARES_MOCK)

    @override_settings(ARES_MOCK=True)
    def test_fetch_ares_data_performs_no_outbound_call(self):
        from users.services import fetch_ares_data

        with (
            mock.patch("requests.get") as m_get,
            mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("outbound DNS attempt")),
        ):
            result = fetch_ares_data("87654321")

        self.assertIsNone(result)
        m_get.assert_not_called()

    @override_settings(ARES_MOCK=False)
    def test_live_ares_requires_explicit_flag(self):
        # ARES_MOCK=False (explicitní opt-in ALLOW_LIVE_EXTERNAL=1) → teprve volá HTTP;
        # HTTP je v tomto testu mockované, takže žádný skutečný odchozí paket nevznikne.
        from users.services import fetch_ares_data

        with mock.patch("requests.get") as m_get:
            m_get.return_value = mock.Mock(status_code=404)
            result = fetch_ares_data("12345678")

        self.assertIsNone(result)
        m_get.assert_called_once()

    def test_ares_endpoint_makes_no_outbound_http(self):
        cache.clear()
        with (
            mock.patch("requests.get") as m_get,
            mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("outbound DNS attempt")),
        ):
            response = self.client.post("/api/users/ares-justice/", {"ico": "12345678"}, format="json")

        m_get.assert_not_called()
        self.assertIn(response.status_code, (200, 404))
        if response.status_code == 404:
            self.assertEqual(response.data.get("error_code"), "ARES_NOT_FOUND")

    @override_settings(ARES_MOCK=True, STAG_MOCK=False)
    def test_session_gate_refuses_real_stag(self):
        from conftest import bl07_isolation_gates

        with self.assertRaises(RuntimeError):
            bl07_isolation_gates()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_session_gate_refuses_smtp_email(self):
        from conftest import bl07_isolation_gates

        with self.assertRaises(RuntimeError):
            bl07_isolation_gates()


class EmailIsolationTests(TestCase):
    """Gap #4 — e-mail je vynuceně in-memory i mimo runner chování Django."""

    def test_test_settings_pin_locmem_email_backend(self):
        self.assertEqual(settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend")

    def test_probe_mail_lands_in_outbox(self):
        from django.core.mail import send_mail

        mail.outbox.clear()
        send_mail("BL-07 probe", "body", "probe@example.com", ["dest@example.com"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["dest@example.com"])
