"""BL-07 — runtime identity guard pro disposable testovací databáze (fail-closed).

Guard odmítne běh test runneru, jehož
cílová databáze neodpovídá schématu jednorázové testovací databáze:

* jméno **obsahuje** ``test`` (bez ohledu na velikost písmen) — pokrývá odvozené
  ``test_<NAME>`` (Django test runner), ``test_test_internhub`` (host výchozí),
  ``test_internhub`` (Docker, ``.env PG_DB=internhub``), ``internhub_test``
  (CI) i unikátní ``bl07_test_<timestamp>``; nebo
* SQLite ``:memory:`` / ``file:...?mode=memory`` — procesní databáze, kterou
  nelze sdílet se serverem.

Schéma vychází z auditu (``lanes/bl07-sandbox-proof.md`` §1.1–1.3 a Gate 2c):
konfigurované ``NAME`` se nikdy nepoužívá přímo — runner operuje na
``test_<NAME>`` (Django ``TEST_DATABASE_PREFIX``), protože ``TEST.NAME``
není nikde explicitně nastaveno.

Kde guard hlídá (viz BL-07 scope):

1. **settings check** — ``app/test_settings.py`` volá
   :func:`assert_runner_db_identity` při načtení; nesoulad = ``ImproperlyConfigured``
   = žádný testovací běh se nerozběhne (fail CLOSED).
2. **E2E reset service** — ``test_support.db_reset.reset_e2e_database``
   má vlastní striktní kontrolu efektivního cíle před delegací na vestavěný
   Django flush; nespoléhá na volitelný runtime guard.
3. **běh testů** — ``conftest.py`` znovu ověří identitu DB, locmem e-mail a
   mock režim externích služeb na začátku každé pytest session.

Aktivace: guard je defaultně **aktivní**, když ``settings.DEBUG`` je True
(test/dev/E2E kontext), nebo když je explicitně zapnut
``settings.DB_IDENTITY_GUARD`` (tak činí ``app/test_settings.py``).
V produkci (``DEBUG=False``) zůstává nečinný → provozní chování se nemění
(``manage.py flush`` ani žádná jiná provozní operace se neblokuje; testovací
reset endpoint je navíc mimo DEBUG neregistrován).

Únikový ventil pouze pro vědomého lidského operátora: env
``BL07_ALLOW_NON_TEST_DB=1`` (guard povolí, ale zapíše varování). Bez něj je
výchozí stav fail-closed.
"""

from __future__ import annotations

import logging
import os

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Zrcadlí django.db.backends.base.creation.TEST_DATABASE_PREFIX.
TEST_DB_PREFIX = "test_"
IN_MEMORY_DB_NAMES = frozenset({":memory:"})
ALLOW_NON_TEST_DB_ENV = "BL07_ALLOW_NON_TEST_DB"


class NonDisposableDatabaseError(RuntimeError):
    """Operace odmítnuta: cílová databáze není disposable test databáze."""


def _is_in_memory(name: str, engine: str = "") -> bool:
    if name in IN_MEMORY_DB_NAMES:
        return True
    return "mode=memory" in name and str(engine).startswith("django.db.backends.sqlite")


def is_disposable_db_name(name, engine: str = "") -> bool:
    """True = jméno odpovídá schématu jednorázové testovací databáze."""
    if not name:
        return False
    name = str(name)
    if _is_in_memory(name, engine):
        return True
    return "test" in name.lower()


def runner_db_name(db_config: dict) -> str | None:
    """Odvozené jméno databáze, na které operuje test runner.

    Replikuje chování Django (``TEST.NAME`` má přednost, jinak
    ``test_ + NAME``); v repozitáři není ``TEST.NAME`` nikde nastaveno.
    """
    test_cfg = db_config.get("TEST") or {}
    test_name = test_cfg.get("NAME")
    if test_name:
        return str(test_name)
    name = db_config.get("NAME")
    if not name:
        return None
    return f"{TEST_DB_PREFIX}{name}"


def assert_runner_db_identity(db_config: dict, *, operation: str = "test runner") -> str:
    """Settings-kontrola (bez DB spojení): runner smí operovat jen na disposable DB.

    Vrací odvozené jméno test DB; při nesouladu hodí ``ImproperlyConfigured``
    (cokoli pod ``app.test_settings`` tedy selže už při načtení nastavení).
    """
    engine = str(db_config.get("ENGINE") or "")
    name = db_config.get("NAME")

    if not name:
        raise ImproperlyConfigured(
            f"BL-07 guard ({operation}): konfigurované jméno databáze je prázdné — "
            "odmítnuto pracovat bez jednoznačné identity DB. Nastav PG_DB na "
            "disposable jméno obsahující 'test' (např. PG_DB=bl07_test_<timestamp>)."
        )

    name = str(name)
    if _is_in_memory(name, engine):
        # Explicit TEST.NAME wins in Django even if the configured NAME is
        # in-memory. Validate that actual test-runner target instead.
        explicit_test_name = (db_config.get("TEST") or {}).get("NAME")
        if not explicit_test_name or _is_in_memory(str(explicit_test_name), engine):
            return str(explicit_test_name or name)
        target = str(explicit_test_name)
        if not is_disposable_db_name(target, engine):
            raise ImproperlyConfigured(
                f"BL-07 guard ({operation}): explicit SQLite TEST.NAME={target!r} "
                "is not a disposable test database; refusing to use a file-backed target."
            )
        return target

    target = runner_db_name(db_config)
    if not target or not is_disposable_db_name(target, engine):
        raise ImproperlyConfigured(
            f"BL-07 guard ({operation}): test runner by operoval na {target!r}, "
            f"což neodpovídá schématu disposable test DB (očekává se jméno "
            f"obsahující 'test', odvozeno od PG_DB={name!r}). Odmítnuto — "
            "fail-closed. Použij PG_DB obsahující 'test'."
        )

    if target == name:
        raise ImproperlyConfigured(
            f"BL-07 guard ({operation}): test runner by operoval přímo na "
            f"nakonfigurované databázi {name!r} (TEST.NAME == NAME) — odmítnuto, "
            "aby se testy nemohly dotknout nedisposable databáze. Nech "
            "TEST.NAME prázdné (runner odvozuje 'test_' + NAME)."
        )

    return target


def assert_runner_db_identities(databases: dict, *, operation: str = "test runner") -> dict[str, str]:
    """Validate every configured runner alias and return its effective target."""
    if not databases:
        raise ImproperlyConfigured(f"BL-07 guard ({operation}): žádné databázové aliasy nejsou nakonfigurovány.")
    return {alias: assert_runner_db_identity(config, operation=f"{operation} alias {alias!r}") for alias, config in databases.items()}


def guard_active() -> bool:
    """Guard je aktivní mimo schválený provoz (produkce = DEBUG=False → nečinný)."""
    from django.conf import settings

    explicit = getattr(settings, "DB_IDENTITY_GUARD", None)
    if explicit is not None:
        return bool(explicit)
    return bool(getattr(settings, "DEBUG", False))


def assert_disposable_db(operation: str, *, connection=None, allow_env: str = ALLOW_NON_TEST_DB_ENV) -> None:
    """Runtime guard: odmítne operaci na nedisposable databázi (fail-closed).

    Neotevírá DB spojení — čte pouze ``connection.settings_dict``.
    """
    if not guard_active():
        return

    if os.environ.get(allow_env) == "1":
        logger.warning(
            "BL-07 guard: operace %r na %r povolena přes %s=1 (explicitní volba operátora).",
            operation,
            (connection or _default_connection()).settings_dict.get("NAME"),
            allow_env,
        )
        return

    if connection is None:
        connection = _default_connection()

    settings_dict = connection.settings_dict
    name = settings_dict.get("NAME")
    engine = str(settings_dict.get("ENGINE") or "")

    if is_disposable_db_name(name, engine):
        return

    raise NonDisposableDatabaseError(
        f"BL-07 guard: odmítnuta operace {operation!r} na nedisposable databázi {name!r} "
        f"(engine={engine}). Povoleno je pouze jméno obsahující 'test' "
        f"(např. PG_DB=bl07_test_<timestamp>, test_internhub, internhub_test) "
        f"nebo SQLite :memory:. Pro vědomou lidskou operaci nastav {allow_env}=1."
    )


def _default_connection():
    from django.db import connection

    return connection


def db_identity_report() -> dict:
    """Diagnostický výstup identity DB (pro gate logy; nezobrazuje credentials)."""
    from django.conf import settings
    from django.db import connection

    db_config = settings.DATABASES.get("default", {})
    return {
        "configured_name": db_config.get("NAME"),
        "engine": db_config.get("ENGINE"),
        "derived_test_db": runner_db_name(db_config),
        "effective_name": connection.settings_dict.get("NAME"),
        "guard_active": guard_active(),
        "disposable_configured": is_disposable_db_name(db_config.get("NAME"), str(db_config.get("ENGINE") or "")),
    }
