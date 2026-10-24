"""BL-07 / PBUG-03 — E2E fixture: praxe + StudentPractice ve stavu ENDED.

Nahrazuje dřívější inline `manage.py shell -c "…pozlátko bez nových řádků…"`
(který byl neplatný Python a běžel s výchozím nastavením, tj. potenciálně
proti nedisposable DB).

Fail-closed pravidla (aligment s backend/app/db_identity.py):
1. `E2E_DB_NAME` musí být výslovně nastaveno (disposable jméno, obsahuje "test");
2. jméno, na které je připojené Django, se MUSÍ rovnat `E2E_DB_NAME`;
3. `assert_disposable_db` (BL-07 guard) musí projít;
jinak skript končí bez jediného zápisu.

Spuštění (z backend/):
    DJANGO_SETTINGS_MODULE=app.test_settings E2E_DB_NAME=bl07_test_<ts> \
    E2E_PRACTICE_TITLE="<title>" python manage.py shell --no-startup < seed_ended_practice.py
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from django.db import connection  # noqa: E402

from app.db_identity import assert_disposable_db, is_disposable_db_name  # noqa: E402

REQUIRED_ENV = "E2E_DB_NAME"
requested_db = os.environ.get(REQUIRED_ENV)
if not requested_db:
    sys.exit(f"REFUSED: {REQUIRED_ENV} (disposable DB name) must be set explicitly — refusing to guess a DB.")

configured_db = connection.settings_dict["NAME"]
if configured_db != requested_db:
    sys.exit(f"REFUSED: connection points at {configured_db!r}, but {REQUIRED_ENV}={requested_db!r} was requested.")

try:
    assert_disposable_db("e2e-evaluace-fixture")
except Exception as exc:  # NonDisposableDatabaseError
    sys.exit(f"REFUSED by BL-07 guard: {exc}")

if not is_disposable_db_name(configured_db, connection.settings_dict.get("ENGINE", "")):
    sys.exit(f"REFUSED: {configured_db!r} does not match the disposable naming scheme.")

title = os.environ.get("E2E_PRACTICE_TITLE")
if not title:
    sys.exit("REFUSED: E2E_PRACTICE_TITLE must be set.")

# --- fixture data (stejná jako dřívější inline skript) -----------------------
from datetime import date, timedelta  # noqa: E402

from practices.models import Practice, PracticeWorkflowState, ProgressStatus  # noqa: E402
from student_practices.models import (  # noqa: E402
    StudentPractice,
    StudentPracticeWorkflowState,
)
from subject.models import Subject  # noqa: E402
from users.models import (  # noqa: E402
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    StudentUser,
)

student = StudentUser.objects.first()
company = OrganizationUser.objects.filter(organization_role=OrganizationRole.OWNER).first()
profile = company.employer_profile if company and company.employer_profile else EmployerProfile.objects.first()
subject = Subject.objects.first()

if not (student and profile and subject):
    sys.exit("REFUSED: seed data incomplete (need student, employer profile and subject) — run the DB reset first.")

practice = Practice.objects.create(
    employer=profile,
    subject=subject,
    title=title,
    description="Eval test",
    responsibilities="Testing",
    available_positions=2,
    start_date=date.today() - timedelta(days=30),
    end_date=date.today() - timedelta(days=5),
    progress_status=ProgressStatus.NOT_STARTED,
    approval_status=ApprovalStatus.APPROVED,
    workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
    contact_user=company,
    is_active=True,
    mentor_name="Mentor E2E",
    contact_email="mentor.e2e@example.com",
)

sp = StudentPractice.objects.create(
    user=student,
    practice=practice,
    application_date=date.today() - timedelta(days=25),
    approval_status=ApprovalStatus.APPROVED,
    progress_status=ProgressStatus.IN_PROGRESS,
    school_approved=True,
    employer_approved=True,
    workflow_state=StudentPracticeWorkflowState.ENDED,
    start_date=practice.start_date,
    end_date=practice.end_date,
    hours_completed=100,
)

print(sp.student_practice_id)
