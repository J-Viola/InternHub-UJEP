# Must set DEBUG before importing settings to avoid production safety checks
import os
import tempfile

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("JWT_ACCESS_TOKEN_REFRESH_TIME", "300")
# Test DB — prefix test_ to prevent accidental use of production database.
# Credentials below are local-dev only; CI/other environments override via env vars.
os.environ.setdefault("PG_DB", "test_internhub")
os.environ.setdefault("PG_USER", "internhub")
os.environ.setdefault("PG_PASSWORD", "1234")
os.environ.setdefault("PG_HOST", "localhost")
os.environ.setdefault("PG_PORT", "5432")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("EMAIL_USER", "")
os.environ.setdefault("EMAIL_PASSWORD", "")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("STAG_MOCK", "True")

# Test document templates live outside the repository and are available under
# both pytest-django and Django's built-in ``manage.py test`` runner.
from docx import Document  # noqa: E402

from .settings import *  # noqa: F403,E402

MEDIA_ROOT = tempfile.mkdtemp(prefix="internhub-test-media-")
_default_documents = os.path.join(MEDIA_ROOT, "default_documents")
os.makedirs(_default_documents, exist_ok=True)
for _template_name in ("default_contract.docx", "default_content.docx", "default_feedback.docx"):
    Document().save(os.path.join(_default_documents, _template_name))
del _default_documents, _template_name

# ---------------------------------------------------------------------------
# BL-07 — izolační gardy (fail-closed). Aktivují se jen mimo schválený provoz;
# produkce (app.settings, DEBUG=False) tyto přepisy nemá → chování se nemění.
# ---------------------------------------------------------------------------

# 1) E-mail: lokální outbox, žádný SMTP spoj (dříve záviselo jen na runneru).
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# 2) DB identity guard: zapnout i mimo DEBUG a přezkoumat načtenou konfiguraci.
DB_IDENTITY_GUARD = True
E2E_RESET_ENABLED = True

# 3) ARES: bez odchozího HTTP, pokud operátor výslovně nepovolí živý režim.
if os.environ.get("ALLOW_LIVE_EXTERNAL") != "1":
    ARES_MOCK = True

# 4) Settings check — runner musí operovat jen na disposable test DB.
#    Nesoulad = ImproperlyConfigured už při načtení nastavení (žádný běh nezačne).
from .db_identity import assert_runner_db_identities  # noqa: E402

assert_runner_db_identities(DATABASES, operation="app.test_settings")  # noqa: F405

ALLOWED_HOSTS = ["*"]

MIGRATION_MODULES = {
    "auth": None,
    "contenttypes": None,
    "default": None,
    "sessions": None,
    "api": None,
    "users": None,
    "practices": None,
    "student_practices": None,
    "department": None,
    "subject": None,
    "admin": None,
    "token_blacklist": None,
    "notifications": None,
}

# Use local memory cache for tests (avoids Redis dependency)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
