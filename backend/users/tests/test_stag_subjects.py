"""Načítání předmětů ze STAGu jen pro aktuální akademický rok a ochrana vazeb s rozběhnutou praxí."""

from datetime import date, timedelta
from unittest import mock

import pytest
from django.test import override_settings

from practices.models import ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import ApprovalStatus, UserSubject, UserSubjectType
from users.services import sync_stag_subjects_for_student
from users.stag_api.real_client import RealStagClient


def _response(status_code=200, payload=None):
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload or {}
    return response


@override_settings(STAG_WS_URL="https://stag.test/ws")
@mock.patch("users.stag_api.real_client.requests.get")
def test_student_subjects_are_limited_to_current_academic_year(get):
    get.side_effect = [_response(payload={"obdobi": "ZS", "akademRok": "2026"}), _response(payload={"predmetStudenta": []})]

    RealStagClient().get_student_subjects("ticket", "A123")

    assert get.call_args_list[0].args[0].endswith("/kalendar/getAktualniObdobiInfo")
    params = get.call_args_list[1].kwargs["params"]
    assert params["rok"] == "2026"
    assert params["semestr"] == "%"


@override_settings(STAG_WS_URL="https://stag.test/ws")
@mock.patch("users.stag_api.real_client.requests.get")
def test_teacher_subjects_are_limited_to_current_academic_year(get):
    get.side_effect = [_response(payload={"akademRok": "2026"}), _response(payload={"predmetUcitele": []})]

    RealStagClient().get_teacher_subjects("ticket", "42")

    assert get.call_args_list[1].kwargs["params"]["rok"] == "2026"


@pytest.mark.parametrize(
    ("today", "expected"),
    [(date(2026, 11, 20), "2026"), (date(2027, 3, 1), "2026"), (date(2027, 9, 30), "2026"), (date(2027, 10, 1), "2027")],
)
@override_settings(STAG_WS_URL="https://stag.test/ws")
@mock.patch("users.stag_api.real_client.requests.get", return_value=_response(status_code=500))
def test_academic_year_falls_back_to_date(get, today, expected):
    with mock.patch("users.stag_api.real_client.date") as fake_date:
        fake_date.today.return_value = today
        assert RealStagClient()._current_academic_year("ticket") == expected


@pytest.mark.django_db
@override_settings(STAG_MOCK=False, DEMO_LOGIN=False)
def test_sync_keeps_subject_with_ongoing_practice(student_user, practice, subject):
    """Předmět z dřívějšího roku s rozběhnutou praxí zůstává aktivní, jiný starý předmět se deaktivuje."""
    old_subject = Subject.objects.create(subject_code="KI/OLD", subject_name="Starý předmět", department=subject.department)
    UserSubject.objects.create(user=student_user, subject=subject, role=UserSubjectType.Student)
    UserSubject.objects.create(user=student_user, subject=old_subject, role=UserSubjectType.Student)
    StudentPractice.objects.create(
        user=student_user,
        practice=practice,
        workflow_state=StudentPracticeWorkflowState.STARTED,
        approval_status=ApprovalStatus.APPROVED,
        progress_status=ProgressStatus.NOT_STARTED,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=60),
    )

    with mock.patch("users.services.get_stag_client") as get_client:
        get_client.return_value.get_student_subjects.return_value = [{"zkratka": "KI/NEW", "nazev": "Nový", "katedra": "KI"}]
        sync_stag_subjects_for_student("ticket", student_user.os_cislo, student_user)

    active = set(UserSubject.objects.filter(user=student_user, is_active=True).values_list("subject__subject_code", flat=True))
    assert active == {subject.subject_code, "KI/NEW"}
