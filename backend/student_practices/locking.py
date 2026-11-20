"""
Řádkové zámky přihlášek a opakování transakce při uváznutí.

Kanonické pořadí zámků (vždy rodič před potomkem):

    Practice (nabídka) → StudentPractice (přihláška) → UploadedDocument (dokument)
    EmployerInvitation (pozvánka) → Practice (nabídka)

Každá transakce, která zamyká víc než jeden z těchto řádků, je musí brát
v tomto pořadí. Jinak dvě souběžné transakce (např. storno nabídky
a schválení smlouvy) mohou uváznout. Přihlášky a dokumenty se proto
nezamykají přímým ``select_for_update()``, ale přes ``lock_student_practice``
a ``lock_document``. Opakované zamčení už držené nabídky ve stejné transakci
(kapacitní kontroly) nečeká, pořadí neporušuje.

``retry_on_deadlock`` zopakuje celou transakci, pokud ji PostgreSQL přesto
ukončí kvůli uváznutí nebo serializaci (pojistka, ne náhrada pořadí).
"""

import functools
import logging
import random
import time

from django.db import OperationalError, transaction

from practices.models import Practice
from student_practices.models import StudentPractice, UploadedDocument

logger = logging.getLogger(__name__)

# deadlock_detected, serialization_failure
RETRYABLE_PGCODES = {"40P01", "40001"}


def lock_student_practice(sp_pk) -> StudentPractice:
    """Zamkne nabídku přihlášky a poté přihlášku; vrací čerstvě načtenou přihlášku."""
    practice_id = StudentPractice.objects.filter(pk=sp_pk).values_list("practice_id", flat=True).get()
    if practice_id is not None:
        Practice.objects.select_for_update().get(pk=practice_id)
    return StudentPractice.objects.select_for_update().get(pk=sp_pk)


def lock_document(document_pk) -> tuple[UploadedDocument, StudentPractice | None]:
    """Zamkne nabídku, přihlášku a nakonec dokument; vrací (dokument, přihláška | None)."""
    sp = UploadedDocument.objects.get(pk=document_pk).student_practice
    if sp is not None:
        sp = lock_student_practice(sp.pk)
    document = UploadedDocument.objects.select_for_update().get(pk=document_pk)
    return document, sp


def _is_retryable(error: OperationalError) -> bool:
    # psycopg2 nese kód v `pgcode`, psycopg 3 v `sqlstate`.
    cause = error.__cause__
    return (getattr(cause, "pgcode", None) or getattr(cause, "sqlstate", None)) in RETRYABLE_PGCODES


def retry_on_deadlock(func=None, *, attempts: int = 3):
    """
    Spustí ``func`` ve vlastní transakci a při uváznutí ji zopakuje.

    Opakovat jde jen nejvnější transakci: volá-li se uvnitř už otevřené
    transakce, funkce proběhne jednou a chybu nechá na vnější úrovni.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if transaction.get_connection().in_atomic_block:
                return fn(*args, **kwargs)
            for attempt in range(1, attempts + 1):
                try:
                    with transaction.atomic():
                        return fn(*args, **kwargs)
                except OperationalError as error:
                    if attempt == attempts or not _is_retryable(error):
                        raise
                    logger.warning("Uváznutí v %s, opakuji transakci (pokus %s/%s).", fn.__qualname__, attempt + 1, attempts)
                    time.sleep(random.uniform(0.05, 0.2) * attempt)

        return wrapper

    return decorator(func) if func is not None else decorator
