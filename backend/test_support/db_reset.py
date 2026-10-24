"""Guarded database reset for explicitly enabled E2E test contexts."""

from django.conf import settings
from django.core.management import call_command
from django.core.management.commands.flush import Command as FlushCommand
from django.db import connections

from app.db_identity import NonDisposableDatabaseError, is_disposable_db_name


def reset_e2e_database(using="default"):
    """Flush one explicitly disposable database alias, never a general DB.

    This deliberately does not use the optional runtime guard: endpoint safety
    must not depend on DEBUG, DB_IDENTITY_GUARD, or the operator bypass env var.
    """
    if not getattr(settings, "E2E_RESET_ENABLED", False):
        raise NonDisposableDatabaseError("E2E database reset is not enabled in this context")

    if using not in connections:
        raise NonDisposableDatabaseError(f"Unknown database alias {using!r}")
    db = connections[using]

    config = db.settings_dict
    name = config.get("NAME")
    engine = str(config.get("ENGINE") or "")
    if not is_disposable_db_name(name, engine):
        raise NonDisposableDatabaseError(f"E2E reset refused non-disposable database {name!r} (engine={engine})")

    call_command(FlushCommand(), database=using, interactive=False)
