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
    return (
        employer_profile.org_users.first()
        if hasattr(employer_profile, "org_users")
        else (employer_profile.__class__._default_manager.none())
    )


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

    dept, _ = Department.objects.get_or_create(name="Informatika", shortcut="KI")
    prof = ProfessorUser.objects.create(
        email="prof@fixture.com",
        first_name="Karel",
        last_name="Novák",
        is_active=True,
        department=dept,
    )
    StagRole.objects.create(user=prof, role=StagRoleEnum.VY.value)
    return prof


@pytest.fixture
def practice(db, employer_profile):
    from datetime import date, timedelta

    from practices.models import Practice, ProgressStatus
    from users.models import ApprovalStatus

    return Practice.objects.create(
        title="Testovací stáž",
        employer=employer_profile,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        approval_status=ApprovalStatus.APPROVED,
        progress_status=ProgressStatus.NOT_STARTED,
    )
