# Must set DEBUG before importing settings to avoid production safety checks
import os

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

from .settings import *  # noqa: F403,E402

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
