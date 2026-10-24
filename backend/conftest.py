"""
pytest-django configuration and shared fixtures.

Run all tests via pytest:
    pytest --ds=app.test_settings

Or via Django's test runner (unchanged):
    python manage.py test --settings=app.test_settings
"""

import django
import pytest
from django.conf import settings

# ---------------------------------------------------------------------------
# pytest-django configuration
# ---------------------------------------------------------------------------


def pytest_configure(config):
    """Set DJANGO_SETTINGS_MODULE when running under pytest."""
    if not settings.configured:
        django.setup()
    bl07_isolation_gates()


def bl07_isolation_gates():
    """BL-07 Gates 2c/3c/4 — runtime kontroly izolace před každou pytest session.

    Fail-closed: bez schváleného testovacího nastavení (``app.test_settings`` /
    audit wrapper) session ani nezačne. Živé externí služby jen při výslovném
    opt-inu ``ALLOW_LIVE_EXTERNAL=1``; e-mail musí být locmem VŽDYCKY.
    """
    import os

    from app.db_identity import assert_runner_db_identities

    allow_live = os.environ.get("ALLOW_LIVE_EXTERNAL") == "1"

    # Gate 2c — identita DB (stejná funkce jako settings check v test_settings).
    assert_runner_db_identities(settings.DATABASES, operation="pytest session")

    # Gate 3c — uvnitř runneru nesmí být SMTP.
    if settings.EMAIL_BACKEND != "django.core.mail.backends.locmem.EmailBackend":
        raise RuntimeError(
            f"BL-07 gate: EMAIL_BACKEND={settings.EMAIL_BACKEND!r} není locmem — "
            "testovací session by mohla odesílat reálný e-mail. Použij "
            "app.test_settings / audit wrapper."
        )

    # Gate 4 — externí služby v mock režimu (STAG + ARES), jinak explicitní opt-in.
    if not allow_live:
        if not getattr(settings, "STAG_MOCK", False):
            raise RuntimeError(
                "BL-07 gate: STAG_MOCK=False — hrozí reálné volání STAG z testů. "
                "Zapni STAG_MOCK nebo povol ALLOW_LIVE_EXTERNAL=1 (výslovný opt-in)."
            )
        if not getattr(settings, "ARES_MOCK", False):
            raise RuntimeError(
                "BL-07 gate: ARES_MOCK=False — hrozí reálné odchozí HTTP do ARES "
                "z testů. Nech ARES_MOCK=True nebo povol ALLOW_LIVE_EXTERNAL=1 "
                "(výslovný opt-in)."
            )


# ---------------------------------------------------------------------------
# Shared fixtures — model factories
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def employer_profile(db):
    from users.models import ApprovalStatus, EmployerProfile, OrganizationUser

    org_user = OrganizationUser.objects.create(
        email="org@fixture.com",
        password="pass",
        first_name="Org",
        last_name="Fixture",
        is_active=True,
    )
    profile = EmployerProfile.objects.create(
        employer_id=org_user.pk,
        company_name="Fixture Corp",
        approval_status=ApprovalStatus.APPROVED,
    )
    org_user.employer_profile = profile
    org_user.save()
    return profile


@pytest.fixture
def org_user(employer_profile):
    return employer_profile.organization_users.first()


@pytest.fixture
def student_user(db):
    from users.models import StudentUser

    return StudentUser.objects.create(
        email="student@fixture.com",
        first_name="Jan",
        last_name="Novák",
        os_cislo="A12345",
        is_active=True,
    )


@pytest.fixture
def professor_user(db):
    from department.models import Department
    from users.models import ProfessorUser, StagRole, StagRoleEnum

    dept, _ = Department.objects.get_or_create(department_name="Informatika", department_code="KI")
    stag_role, _ = StagRole.objects.get_or_create(
        role=StagRoleEnum.VY,
        defaults={"role_name": "Vyučující", "description": "STAG teacher role"},
    )
    prof = ProfessorUser.objects.create(
        email="prof@fixture.com",
        first_name="Karel",
        last_name="Novák",
        is_active=True,
        department=dept,
        stag_role=stag_role,
    )
    return prof


@pytest.fixture
def department(db):
    """Default department for fixtures."""
    from department.models import Department

    dept, _ = Department.objects.get_or_create(
        department_name="Informatika",
        defaults={"department_code": "KI"},
    )
    return dept


@pytest.fixture
def subject(db, department):
    """Default subject for fixtures, linked to department."""
    from subject.models import Subject

    subj, _ = Subject.objects.get_or_create(
        subject_code="KI/BOP",
        defaults={
            "subject_name": "Odborná praxe",
            "department": department,
            "min_hours": 480,
        },
    )
    return subj


@pytest.fixture
def practice(db, employer_profile, subject):
    from datetime import date, timedelta

    from practices.models import Practice, ProgressStatus
    from users.models import ApprovalStatus

    return Practice.objects.create(
        title="Testovací stáž",
        employer=employer_profile,
        subject=subject,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        approval_status=ApprovalStatus.APPROVED,
        progress_status=ProgressStatus.NOT_STARTED,
    )
