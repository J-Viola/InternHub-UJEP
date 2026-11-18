"""A-31 — CSP ve dvou vrstvách: nginx pro SPA, Django pro administraci a dokumentaci API.

Testy hlídají, že se obě konfigurace nerozejdou: vložené skripty nesmí povolit ani jedna,
vložené styly smí jen jako atributy ``style="..."`` (výjimkou je stránka Swagger UI).
"""

import re
from pathlib import Path

import pytest
from django.test import TestCase

from users.models import OrganizationUser

BACKEND_DIR = Path(__file__).resolve().parents[2]
NGINX_CONF = BACKEND_DIR.parent / ".docker" / "Frontend" / "nginx.conf"


def parse_policy(header):
    """Vrátí direktivy CSP hlavičky jako slovník název → seznam hodnot."""
    policy = {}
    for part in header.split(";"):
        tokens = part.split()
        if tokens:
            policy[tokens[0]] = tokens[1:]
    return policy


def nginx_spa_policy():
    """Vytáhne z nginx.conf CSP, kterou dostává HTML a statika SPA."""
    text = NGINX_CONF.read_text(encoding="utf-8")
    block = re.search(r"map\s+\$request_uri\s+\$csp_value\s*\{(?P<body>.*?)\n\}", text, re.S)
    assert block, "v nginx.conf chybí map $request_uri $csp_value"
    default = re.search(r'default\s+"(?P<policy>[^"]+)"', block.group("body"))
    assert default, "v mapě chybí výchozí CSP pro SPA"
    return default.group("policy")


def external_script_tags(html):
    """Vrátí značky <script>, které nemají src (tedy vložené skripty)."""
    return [tag for tag in re.findall(r"<script\b[^>]*>", html) if "src=" not in tag]


@pytest.mark.skipif(
    not NGINX_CONF.exists(),
    reason="nginx.conf není v backend image; běžnou odpověď SPA ověřuje scripts/verify_prod_stack.sh",
)
class NginxSpaCspTests(TestCase):
    """SPA dostává CSP z nginx; Django ji pro /api/ a /admin/ nepřidává."""

    def test_spa_policy_forbids_inline_scripts(self):
        policy = parse_policy(nginx_spa_policy())
        self.assertEqual(policy["script-src"], ["'self'"])

    def test_spa_policy_allows_only_style_attributes(self):
        policy = parse_policy(nginx_spa_policy())
        self.assertEqual(policy["style-src-attr"], ["'unsafe-inline'"])
        self.assertNotIn("'unsafe-inline'", policy["style-src-elem"])
        self.assertIn("https://fonts.googleapis.com", policy["style-src-elem"])

    def test_django_paths_have_no_nginx_policy(self):
        """Na /api/ a /admin/ posílá hlavičku Django, nginx ji nepřidává."""
        text = NGINX_CONF.read_text(encoding="utf-8")
        block = re.search(r"map\s+\$request_uri\s+\$csp_value\s*\{(?P<body>.*?)\n\}", text, re.S)
        self.assertRegex(block.group("body"), r'~?\^/\(api\|admin\)/\s+""')


class DjangoCspTests(TestCase):
    """Django nastavuje CSP administraci, dokumentaci API i API odpovědím."""

    def test_admin_has_no_inline_scripts_or_styles(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        policy = parse_policy(response["Content-Security-Policy"])
        self.assertEqual(policy["script-src"], ["'self'"])
        self.assertNotIn("'unsafe-inline'", policy["style-src-elem"])
        self.assertEqual(policy["style-src-attr"], ["'unsafe-inline'"])

    def test_admin_change_form_uses_external_scripts_only(self):
        user = OrganizationUser.objects.create_superuser(email="csp-admin@example.invalid", password="x")
        self.client.force_login(user)
        response = self.client.get(f"/admin/users/organizationuser/{user.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(external_script_tags(response.content.decode()), [])

    def test_swagger_ui_needs_no_inline_scripts(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(external_script_tags(html), [])
        self.assertIn("?script=", html)
        policy = parse_policy(response["Content-Security-Policy"])
        self.assertEqual(policy["script-src"], ["'self'"])
        # Swagger UI si vkládá vlastní <style>; zablokuje se jen kosmetický styl.
        self.assertNotIn("'unsafe-inline'", policy["style-src-elem"])

    def test_swagger_ui_split_script_is_served(self):
        response = self.client.get("/api/docs/?script=")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertIn("SwaggerUIBundle", response.content.decode())
