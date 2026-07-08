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
