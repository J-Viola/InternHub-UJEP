"""Kanonické pořadí zámků (nabídka → přihláška → dokument) a opakování transakce při uváznutí."""

import re
from contextlib import nullcontext
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import pytest
from django.db import OperationalError, connection
from django.test.utils import CaptureQueriesContext

from practices.models import ProgressStatus
from student_practices.locking import lock_document, lock_student_practice, retry_on_deadlock
from student_practices.models import DocumentType, StudentPractice, StudentPracticeWorkflowState, UploadedDocument
from users.models import ApprovalStatus


@pytest.fixture
def student_practice(practice, student_user):
    return StudentPractice.objects.create(
        user=student_user,
        practice=practice,
        workflow_state=StudentPracticeWorkflowState.APPLIED,
        approval_status=ApprovalStatus.PENDING,
        progress_status=ProgressStatus.NOT_STARTED,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=60),
    )


def _locked_tables(queries):
    return [re.search(r'FROM "(\w+)"', q["sql"]).group(1) for q in queries if "FOR UPDATE" in q["sql"]]


@pytest.mark.django_db
def test_lock_student_practice_locks_practice_first(student_practice):
    with CaptureQueriesContext(connection) as ctx:
        locked = lock_student_practice(student_practice.pk)

    assert locked.pk == student_practice.pk
    assert _locked_tables(ctx.captured_queries) == ["practices", "student_practices"]


@pytest.mark.django_db
def test_lock_document_locks_practice_then_application_then_document(student_practice):
    document = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT)
    student_practice.contract_document = document
    student_practice.save(update_fields=["contract_document"])

    with CaptureQueriesContext(connection) as ctx:
        locked_document, locked_sp = lock_document(document.pk)

    assert (locked_document.pk, locked_sp.pk) == (document.pk, student_practice.pk)
    assert _locked_tables(ctx.captured_queries) == ["practices", "student_practices", "uploaded_documents"]


@pytest.mark.django_db
def test_lock_document_without_application_locks_only_document():
    document = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT)

    with CaptureQueriesContext(connection) as ctx:
        _, locked_sp = lock_document(document.pk)

    assert locked_sp is None
    assert _locked_tables(ctx.captured_queries) == ["uploaded_documents"]


def _transaction_body(side_effect):
    """Skutečná funkce (dekorátor čte __qualname__) obalující mock s daným průběhem."""
    calls = mock.Mock(side_effect=side_effect)

    def body():
        return calls()

    body.calls = calls
    return body


def _operational_error(pgcode):
    cause = Exception("driver error")
    cause.pgcode = pgcode
    error = OperationalError("db error")
    error.__cause__ = cause
    return error


@pytest.fixture
def outermost_transaction():
    """Simuluje volání mimo otevřenou transakci (testy samy běží v transakci)."""
    with (
        mock.patch("student_practices.locking.transaction.get_connection") as get_connection,
        mock.patch("student_practices.locking.transaction.atomic", return_value=nullcontext()),
        mock.patch("student_practices.locking.time.sleep") as sleep,
    ):
        get_connection.return_value.in_atomic_block = False
        yield sleep


def test_retry_on_deadlock_repeats_transaction(outermost_transaction):
    func = _transaction_body([_operational_error("40P01"), _operational_error("40001"), "ok"])

    assert retry_on_deadlock(func)() == "ok"
    assert func.calls.call_count == 3
    assert outermost_transaction.call_count == 2


def test_retry_on_deadlock_gives_up_after_attempts(outermost_transaction):
    func = _transaction_body(_operational_error("40P01"))

    with pytest.raises(OperationalError):
        retry_on_deadlock(attempts=2)(func)()
    assert func.calls.call_count == 2


def test_retry_on_deadlock_does_not_retry_other_errors(outermost_transaction):
    func = _transaction_body(_operational_error("57014"))

    with pytest.raises(OperationalError):
        retry_on_deadlock(func)()
    assert func.calls.call_count == 1


def test_retry_on_deadlock_inside_transaction_runs_once():
    func = _transaction_body(_operational_error("40P01"))

    with mock.patch("student_practices.locking.transaction.get_connection") as get_connection:
        get_connection.return_value.in_atomic_block = True
        with pytest.raises(OperationalError):
            retry_on_deadlock(func)()
    assert func.calls.call_count == 1


def test_no_direct_row_locks_on_applications_or_documents():
    """Přihlášky a dokumenty se zamykají jen přes student_practices.locking."""
    backend = Path(__file__).resolve().parents[2]
    pattern = re.compile(r"(StudentPractice|UploadedDocument)\.objects\.select_for_update\(")
    offenders = [
        str(path.relative_to(backend))
        for path in backend.rglob("*.py")
        if "tests" not in path.parts and path.name != "locking.py" and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
