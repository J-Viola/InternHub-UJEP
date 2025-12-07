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
