"""BL-08 GO-5 — deterministický demo seed (`manage.py seed_demo`, BL08-SEED-v1).

- deterministické F1–F9 (+ F4b opravný stav) fixture po seedu (stavy + vazby),
- dosažitelnost F1–F8 stavů ihned po seedu (startovní stavy demo aktů 1–8),
- idempotence opakovaného běhu (stabilní počty),
- ``--reset`` odmítnut na nedisposable DB (BL-07 guard) a průchodný
  na disposable (SQLite :memory: pod audit wrapperem).
"""

import io
import os
from datetime import date
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from department.models import Department
from practices.models import Practice
from student_practices.models import (
    DocumentStatus,
    Evaluation,
    PracticeRegistration,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from subject.models import Subject
from users.models import ActionLog, EmployerProfile

SEED_ID = "BL08-SEED-v1"
SPEC_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "demo_seed_spec.json"
DEMO_PASSWORD = "bl08-demo-test-pw"
DEMO_EMAILS = [
    "demo.student@test.local",
    "demo.student2@test.local",
    "demo.garant@test.local",
    "demo.vk@test.local",
    "demo.org@test.local",
    "demo.admin@test.local",
    "demo.foreign@test.local",
]


def run_seed(*args):
    out = io.StringIO()
    call_command("seed_demo", "--password", DEMO_PASSWORD, *args, stdout=out)
    return out.getvalue()


class SeedDemoCommandTests(TestCase):
    def test_seed_creates_deterministic_f1_f9_fixtures(self):
        output = run_seed("--spec", str(SPEC_PATH))

        # verifikační tabulka ve stdout + verifikace prošla
        self.assertIn("Seed OK", output)
        self.assertIn(SEED_ID, output)
        self.assertIn("F9: pending žádost o storno", output)

        # role účtů — přesně 7, doména .test.local, heslo nastaveno
        users = get_user_model().objects.filter(email__in=DEMO_EMAILS)
        self.assertEqual(users.count(), 7)
        for user in users:
            self.assertTrue(user.email.endswith("@test.local"), user.email)
        student = get_user_model().objects.get(email="demo.student@test.local")
        self.assertTrue(student.check_password(DEMO_PASSWORD))
        admin = get_user_model().objects.get(email="demo.admin@test.local")
        self.assertTrue(admin.is_superuser)

        # organizace: syntetický profil, žádné reálné IČO
        # (EmployerProfile.employer_id je AUTO PK — vazba je na straně
        # OrganizationUser.employer_profile, viz BL-02 fixture pattern)
        from users.models import OrganizationUser

        org_user = OrganizationUser.objects.get(email="demo.org@test.local")
        employer = EmployerProfile.objects.get(pk=org_user.pk)  # profile PK == org pk (BL-02 pattern)
        self.assertTrue(employer.company_name.startswith("SYNTHETIC DEMO DATA"))
        self.assertEqual(employer.ico, "00000000")

        st = StudentPracticeWorkflowState
        # F1: CONTRACTED obsazuje jediné místo
        f1 = StudentPractice.objects.get(practice__title="DEMO Kapacita 1")
        self.assertEqual(f1.workflow_state, st.CONTRACTED)
        self.assertEqual(f1.practice.available_positions, 1)
        self.assertTrue(f1.school_approved)
        self.assertTrue(f1.employer_approved)
        # F2/F3
        f2 = StudentPractice.objects.get(practice__title="DEMO Standard")
        self.assertEqual(f2.workflow_state, st.APPLIED)
        f3 = StudentPractice.objects.get(practice__title="DEMO Předsmluvní")
        self.assertEqual(f3.workflow_state, st.AWAITING_CONTRACT)
        self.assertFalse(f3.school_approved)
        self.assertFalse(f3.employer_approved)
        # F4: AWAITING_DOCUMENTS + CONTRACT doklad PENDING
        f4 = StudentPractice.objects.get(practice__title="DEMO Smlouvy")
        self.assertEqual(f4.workflow_state, st.AWAITING_DOCUMENTS)
        self.assertIsNotNone(f4.contract_document)
        self.assertEqual(f4.contract_document.status, DocumentStatus.PENDING)
        # F4b (additive): DOCUMENTS_RESUBMITTED = review-pending oprava (13)
        f4b = StudentPractice.objects.get(practice__title="DEMO Oprava")
        self.assertEqual(f4b.workflow_state, st.DOCUMENTS_RESUBMITTED)
        self.assertIsNotNone(f4b.contract_document)
        self.assertEqual(f4b.contract_document.status, DocumentStatus.PENDING)
        # F5
        f5 = StudentPractice.objects.get(practice__title="DEMO Smlouvy 2")
        self.assertEqual(f5.workflow_state, st.CONTRACTED)
        # F6: ENDED bez Evaluation (completion gate demo)
        f6 = StudentPractice.objects.get(practice__title="DEMO Dokončení")
        self.assertEqual(f6.workflow_state, st.ENDED)
        self.assertFalse(Evaluation.objects.filter(student_practice=f6).exists())
        # F7: employment_type placeholder triáda
        self.assertEqual(Practice.objects.get(title="DEMO Úvazek A").employment_type, "uvazek_0_5")
        self.assertEqual(Practice.objects.get(title="DEMO Úvazek B").employment_type, "uvazek_1_0")
        self.assertEqual(Practice.objects.get(title="DEMO Úvazek C").employment_type, "")
        # F8: nic předseedováno — externí praxe vzniká až v akci 7
        self.assertFalse(Practice.objects.filter(title__icontains="externí").exists())
        # F9: pending žádost o storno (C02-A) na loňské registraci
        f9 = StudentPractice.objects.get(practice__title="DEMO Storno")
        self.assertIsNotNone(f9.cancellation_requested_at)
        self.assertIsNone(f9.cancellation_resolved_at)
        self.assertFalse(f9.is_cancelled)
        self.assertEqual(f9.year, date.today().year - 1)
        self.assertIn("žádost o storno", f9.cancellation_reason)

        # BL-10 registrace: 3 klíče (student/rok-current, student2/rok-current, student/rok-minulý)
        self.assertEqual(PracticeRegistration.objects.filter(student__email__in=DEMO_EMAILS).count(), 3)
        # seed_id zapsán v DB
        marker = ActionLog.objects.filter(object_type="DemoSeed", action_description=SEED_ID).first()
        self.assertIsNotNone(marker)
        # department/subject správně propojen
        subject = Subject.objects.get(subject_code="DEMO-PRAXE")
        self.assertEqual(subject.subject_manager.email, "demo.garant@test.local")
        self.assertEqual(subject.department.department_code, "DEMO-KI")
        self.assertTrue(Department.objects.filter(department_code="DEMO-MA").exists())

    def test_f1_f8_fixture_states_reachable_after_seed(self):
        """F1–F8: po seedu jsou startovní stavy demo aktů 1–8 dosažitelné."""
        from practices.services import PracticeService
        from users.models import StudentUser

        run_seed("--spec", str(SPEC_PATH))
        st = StudentPracticeWorkflowState

        # F1 — jediné místo obsazeno CONTRACTED → třetí žádost = CAPACITY_FULL
        # (akt 1 očekává 400); skutečná cesta službou, ne jen kontrola stavu
        foreign = StudentUser.objects.get(email="demo.foreign@test.local")
        capacity_practice = Practice.objects.get(title="DEMO Kapacita 1")
        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(foreign, capacity_practice.pk)
        self.assertIn("CAPACITY_FULL", str(cm.exception))
        self.assertEqual(StudentPractice.objects.count(), 8)  # žádná nová SP

        # F2 — APPLIED (akt 2: review schválí/zamítne)
        self.assertEqual(StudentPractice.objects.get(practice__title="DEMO Standard").workflow_state, st.APPLIED)
        # F3 — AWAITING_CONTRACT, obě osy=False (akt 3: brána AXES_INCOMPLETE)
        f3 = StudentPractice.objects.get(practice__title="DEMO Předsmluvní")
        self.assertEqual(f3.workflow_state, st.AWAITING_CONTRACT)
        self.assertFalse(f3.school_approved)
        self.assertFalse(f3.employer_approved)
        # F4 — AWAITING_DOCUMENTS + CONTRACT doklad PENDING (akt 4, krok 1)
        f4 = StudentPractice.objects.get(practice__title="DEMO Smlouvy")
        self.assertEqual(f4.workflow_state, st.AWAITING_DOCUMENTS)
        self.assertIsNotNone(f4.contract_document)
        self.assertEqual(f4.contract_document.status, DocumentStatus.PENDING)
        # F4b — DOCUMENTS_RESUBMITTED (akt 4, kroky 2–6: review-pending oprava)
        f4b = StudentPractice.objects.get(practice__title="DEMO Oprava")
        self.assertEqual(f4b.workflow_state, st.DOCUMENTS_RESUBMITTED)
        self.assertIsNotNone(f4b.contract_document)
        self.assertEqual(f4b.contract_document.status, DocumentStatus.PENDING)
        # F5 — CONTRACTED (akt 5: žádost o storno)
        self.assertEqual(StudentPractice.objects.get(practice__title="DEMO Smlouvy 2").workflow_state, st.CONTRACTED)
        # F6 — ENDED bez Evaluation (akt 6: completion gate)
        f6 = StudentPractice.objects.get(practice__title="DEMO Dokončení")
        self.assertEqual(f6.workflow_state, st.ENDED)
        self.assertFalse(Evaluation.objects.filter(student_practice=f6).exists())
        # F7 — employment triáda uvazek_0_5 / uvazek_1_0 / "" (akt 8: filtr)
        self.assertEqual(
            [Practice.objects.get(title=t).employment_type for t in ("DEMO Úvazek A", "DEMO Úvazek B", "DEMO Úvazek C")],
            ["uvazek_0_5", "uvazek_1_0", ""],
        )
        # F8 — žádná externí praxe předseedováno → akt 7 si ji vytvoří sám
        self.assertFalse(Practice.objects.filter(is_external=True).exists())

    def test_seed_is_idempotent(self):
        def snapshot():
            return {
                "users": get_user_model().objects.filter(email__in=DEMO_EMAILS).count(),
                "practices": Practice.objects.filter(title__startswith="DEMO").count(),
                "sps": StudentPractice.objects.filter(practice__title__startswith="DEMO").count(),
                "registrations": PracticeRegistration.objects.filter(student__email__in=DEMO_EMAILS).count(),
                "docs": StudentPractice.objects.filter(practice__title="DEMO Smlouvy")[0].contract_document_id,
                "markers": ActionLog.objects.filter(object_type="DemoSeed", action_description=SEED_ID).count(),
            }

        run_seed("--spec", str(SPEC_PATH))
        first = snapshot()
        output = run_seed("--spec", str(SPEC_PATH))  # opakovaný běh
        second = snapshot()

        self.assertEqual(first, second)  # stabilní počty i vazby
        self.assertIn("Seed OK", output)
        # stavová fixture nezměněna opakovaným během
        f3 = StudentPractice.objects.get(practice__title="DEMO Předsmluvní")
        self.assertEqual(f3.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertEqual(first["markers"], 1)

    def test_reset_refused_on_non_disposable_db(self):
        run_seed("--spec", str(SPEC_PATH))
        sp_before = StudentPractice.objects.filter(practice__title__startswith="DEMO").count()
        self.assertGreater(sp_before, 0)

        # BL-07 guard: nedisposable jméno → --reset odmítnut, nic smazáno
        with (
            mock.patch.dict(connection.settings_dict, {"NAME": "internhub_prod"}),
            # dev kontejner má BL07_ALLOW_NON_TEST_DB=1 → test musí běžet bez operátorské výjimky
            mock.patch.dict(os.environ, clear=False),
            mock.patch("app.management.commands.seed_demo.Command._reset") as destructive_reset,
        ):
            os.environ.pop("BL07_ALLOW_NON_TEST_DB", None)
            with self.assertRaises(CommandError) as cm:
                call_command("seed_demo", "--password", DEMO_PASSWORD, "--spec", str(SPEC_PATH), "--reset", stdout=io.StringIO())
        destructive_reset.assert_not_called()
        self.assertIn("BL-07", str(cm.exception))

        # data intact — žádný demo řádek nesmazán
        self.assertEqual(StudentPractice.objects.filter(practice__title__startswith="DEMO").count(), sp_before)
        self.assertTrue(ActionLog.objects.filter(object_type="DemoSeed").exists())

    def test_reset_on_disposable_db_reseeds_cleanly(self):
        run_seed("--spec", str(SPEC_PATH))
        sp_before = StudentPractice.objects.filter(practice__title__startswith="DEMO").count()

        # SQLite :memory: pod audit wrapperem = disposable → --reset povolen + reseed
        output = run_seed("--spec", str(SPEC_PATH), "--reset")

        self.assertIn("demo řádky smazány", output)
        self.assertIn("Seed OK", output)
        self.assertEqual(StudentPractice.objects.filter(practice__title__startswith="DEMO").count(), sp_before)
