# Must set DEBUG before importing settings to avoid production safety checks
import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("JWT_ACCESS_TOKEN_REFRESH_TIME", "300")
os.environ.setdefault("PG_DB", "test_db")
os.environ.setdefault("PG_USER", "test_user")
os.environ.setdefault("PG_PASSWORD", "test_password")
os.environ.setdefault("PG_HOST", "localhost")
os.environ.setdefault("PG_PORT", "5432")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("EMAIL_USER", "")
os.environ.setdefault("EMAIL_PASSWORD", "")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("STAG_MOCK", "True")

from .settings import *  # noqa: F403,E402

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
