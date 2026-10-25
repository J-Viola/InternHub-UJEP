"""BL-10 — registrace předmětu (Schema Option A) + Q1-A/Q3-A/C03 identita.

Rozhodnutí (bl01-decisions.md Round 5 + bl10-domain-options.md dossier):
- Q2-A: registrace = (student, subject, year); N vztahů neomezených; re-entry OK.
- Q1-A: součet hodin registrace = jen nestornované vztahy (countable_hours).
- Q3-A: dokončení vyžaduje evaluace VŠECH vztahů registrace.
- Q4-A: backfill auto-group + fallbacky (year z datumů; subject/user NULL →
  manuální triáž, logováno); nikdy se data nemažou; idempotentní.
- C03: blok nové žádosti vázán na plnou identitu registrace (student, subject,
  year); legacy řádky bez registration fallbackují předmětově (fail-closed).

Vše syntetické; běh izolovanými test settings (audit verification wrapper).
"""

import importlib
from datetime import date, timedelta

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    EmployerInvitation,
    EmployerInvitationStatus,
    Evaluation,
    PracticeRegistration,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.services import (
    StudentPracticeService,
    ensure_practice_registration,
)
from student_practices.tests.test_bl03_workflow import BL03FixtureMixin
from users.models import ApprovalStatus

BACKFILL = importlib.import_module("student_practices.migrations.0024_practiceregistration_studentpractice_registration_and_more")


def make_practice_no_subject(title, employer):
    """Mixin ``make_practice`` defaultuje předmět, i když se předá None —
    řádek s NULL předmětem (Q4-A triáž) vytvoříme přímo přes model."""
    return Practice.objects.create(
        title=title,
        description="Syntetická BL10 praxe bez předmětu",
        employer=employer,
        subject=None,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=40),
        is_active=True,
        approval_status=ApprovalStatus.APPROVED,
        progress_status=ProgressStatus.NOT_STARTED,
        workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        available_positions=10,
    )


class Bl10RegistrationCreationTests(BL03FixtureMixin, TestCase):
    """Vytváření a vazba registrace na každé cestě vzniku StudentPractice."""

    APPLY_URL = "/api/practices/student/apply/"
    APPROVE_URL = "/api/student-practices/employer-invitation/approve/"

    def test_ensure_registration_get_or_create_idempotent(self):
        r1 = ensure_practice_registration(self.owner_student, self.subject.subject_id, 2026)
        r2 = ensure_practice_registration(self.owner_student, self.subject.subject_id, 2026)
        self.assertIsNotNone(r1)
        self.assertEqual(r1.pk, r2.pk)

        # jiný rok → jiná registrace; jiný předmět → jiná registrace
        r_other_year = ensure_practice_registration(self.owner_student, self.subject.subject_id, 2025)
        self.assertNotEqual(r1.pk, r_other_year.pk)
        r_other_subject = ensure_practice_registration(self.owner_student, self.subject_other.subject_id, 2026)
        self.assertNotEqual(r1.pk, r_other_subject.pk)

    def test_ensure_registration_none_without_subject_or_student(self):
        self.assertIsNone(ensure_practice_registration(self.owner_student, None, 2026))
        self.assertIsNone(ensure_practice_registration(None, self.subject.subject_id, 2026))

    def test_apply_creates_registration_link(self):
        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post(self.APPLY_URL, {"practice": self.practice.practice_id}, format="json")

        self.assertEqual(response.status_code, 201)
        sp = StudentPractice.objects.get(user=self.owner_student, practice=self.practice)
        self.assertIsNotNone(sp.registration)
        self.assertEqual(sp.registration.student_id, self.owner_student.pk)
        self.assertEqual(sp.registration.subject_id, self.subject.subject_id)
        self.assertEqual(sp.registration.year, date.today().year)

    def test_invitation_accept_creates_registration_link(self):
        invitation = EmployerInvitation.objects.create(
            employer=self.employer,
            user=self.owner_student,
            practice=self.practice_same_subject,
            status=EmployerInvitationStatus.PENDING,
            submission_date=date.today(),
        )
        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post(
            self.APPROVE_URL,
            {"invitation_id": invitation.invitation_id, "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        sp = StudentPractice.objects.get(user=self.owner_student, practice=self.practice_same_subject)
        self.assertIsNotNone(sp.registration)
        self.assertEqual(sp.registration.subject_id, self.subject.subject_id)
        self.assertEqual(sp.registration.year, date.today().year)

    def test_reapply_creates_registration_link(self):
        sp1 = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.CONTRACTED)
        # sp1 patří do stejné registrace jako nový vztah (Q2-A re-entry)
        sp1.registration = ensure_practice_registration(self.owner_student, self.subject.subject_id, date.today().year)
        sp1.save(update_fields=["registration"])
        StudentPracticeService.cancel_student_practice(sp1, self.garant, "BL10 reentry")
        # legacy C03: nevyřízené storno blokuje reapply — nevyřešit je rozhodnutím resolvery
        StudentPracticeService.resolve_cancellation(sp1, self.garant)
        sp1.refresh_from_db()

        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post(f"/api/student-practices/reapply/{self.practice.practice_id}/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        sp2 = StudentPractice.objects.get(user=self.owner_student, practice=self.practice, is_cancelled=False)
        self.assertIsNotNone(sp2.registration)
        self.assertEqual(sp2.registration.subject_id, self.subject.subject_id)
        # re-entry: nový vztah sdílí tutéž registraci jako stornovaný (Q2-A)
        self.assertEqual(sp2.registration_id, sp1.registration_id)

    def test_external_create_apply_creates_registration_link(self):
        payload = {
            "employer_name": "BL10 External Org",
            "contact_person": "BL10 Contact",
            "contact_email": "contact-bl10@audit.invalid",
            "ico": "12345678",
            "address": "BL10 address",
            "contact_phone": "+420000000000",
            "external_details_file": SimpleUploadedFile("bl10.pdf", b"%PDF-1.4 bl10", content_type="application/pdf"),
            "subject_id": self.subject.subject_id,
            "title": "BL10 individuální praxe",
            "description": "Syntetické BL10 podání",
            "start_date": (date.today() + timedelta(days=10)).strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }

        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post("/api/practices/external/", payload)

        self.assertEqual(response.status_code, 201, response.data)
        sp = StudentPractice.objects.get(user=self.owner_student, practice_id=response.data["practice_id"])
        self.assertIsNotNone(sp.registration)
        self.assertEqual(sp.registration.subject_id, self.subject.subject_id)
        self.assertEqual(sp.registration.year, date.today().year)

    def test_unbounded_n_shares_one_registration(self):
        """Q2-A: N vztahů jedné registrace (i u stejného zaměstnavatele)
        bez horní hranice — unique_active_student_practice_per_user N neomezuje."""
        practices = [
            self.practice,
            self.practice_same_subject,
            self.make_practice(title="BL10 N-tý vztah"),
        ]
        sps = []
        for practice in practices:
            self.client.force_authenticate(user=self.owner_student)
            response = self.client.post(self.APPLY_URL, {"practice": practice.practice_id}, format="json")
            self.assertEqual(response.status_code, 201)
            sps.append(StudentPractice.objects.get(user=self.owner_student, practice=practice))

        registration_ids = {sp.registration_id for sp in sps}
        self.assertEqual(len(registration_ids), 1)  # jedna registrace, N vztahů
        self.assertEqual(len(sps), 3)


class Bl10BackfillMigrationTests(BL03FixtureMixin, TestCase):
    """Q4-A: data migrace backfill — auto-group + schválené fallbacky,
    idempotentní, žádný řádek se nemaže."""

    @staticmethod
    def _run_backfill():
        BACKFILL.backfill_registrations(apps, None)

    def test_backfill_groups_by_registration_identity(self):
        sp_a = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.APPLIED)
        sp_b = self.make_sp(self.owner_student, practice=self.practice_same_subject, state=StudentPracticeWorkflowState.APPLIED)
        sp_old_year = self.make_sp(
            self.owner_student,
            practice=self.make_practice(title="BL10 starý rok", subject=self.subject),
            state=StudentPracticeWorkflowState.APPLIED,
        )
        StudentPractice.objects.filter(pk=sp_old_year.pk).update(year=2025)
        sp_other_subject = self.make_sp(
            self.owner_student, practice=self.practice_other_subject, state=StudentPracticeWorkflowState.APPLIED
        )

        self._run_backfill()

        sp_a.refresh_from_db()
        sp_b.refresh_from_db()
        sp_old_year.refresh_from_db()
        sp_other_subject.refresh_from_db()
        # stejný (student, subject, year) → tutéž registraci
        self.assertIsNotNone(sp_a.registration_id)
        self.assertEqual(sp_a.registration_id, sp_b.registration_id)
        self.assertEqual(sp_a.registration.year, date.today().year)
        # jiný rok → jiná registrace; jiný předmět → jiná registrace (I3)
        self.assertNotEqual(sp_a.registration_id, sp_old_year.registration_id)
        self.assertEqual(sp_old_year.registration.year, 2025)
        self.assertNotEqual(sp_a.registration_id, sp_other_subject.registration_id)
        self.assertEqual(PracticeRegistration.objects.filter(student=self.owner_student).count(), 3)

    def test_backfill_derives_year_from_dates(self):
        sp_app_date = self.make_sp(
            self.owner_student,
            practice=self.make_practice(title="BL10 derived app-date", subject=self.subject),
            state=StudentPracticeWorkflowState.APPLIED,
        )
        StudentPractice.objects.filter(pk=sp_app_date.pk).update(year=None, application_date=date(2024, 3, 1))
        sp_start_only = self.make_sp(
            self.owner_student,
            practice=self.make_practice(title="BL10 derived start-date", subject=self.subject),
            state=StudentPracticeWorkflowState.APPLIED,
        )
        StudentPractice.objects.filter(pk=sp_start_only.pk).update(year=None, application_date=None)

        self._run_backfill()

        sp_app_date.refresh_from_db()
        sp_start_only.refresh_from_db()
        self.assertIsNone(sp_app_date.year)  # řádek se needituje — odvození jen pro klíč
        self.assertEqual(sp_app_date.registration.year, 2024)  # z application_date
        self.assertEqual(sp_start_only.registration.year, sp_start_only.start_date.year)  # ze start_date

    def test_backfill_triage_rows_never_dropped(self):
        sp_no_subject = self.make_sp(
            self.owner_student,
            practice=make_practice_no_subject("BL10 bez předmětu", self.employer),
            state=StudentPracticeWorkflowState.APPLIED,
        )
        sp_no_user = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.APPLIED)
        StudentPractice.objects.filter(pk=sp_no_user.pk).update(user=None)

        with self.assertLogs("bl10.registration_backfill", level="WARNING") as captured:
            self._run_backfill()

        sp_no_subject.refresh_from_db()
        sp_no_user.refresh_from_db()
        # žádný řádek zmizel ani se nepřepsal jinak než logem triáže
        self.assertEqual(StudentPractice.objects.count(), 2)
        self.assertIsNone(sp_no_subject.registration_id)
        self.assertIsNone(sp_no_user.registration_id)
        self.assertEqual(sp_no_subject.workflow_state, StudentPracticeWorkflowState.APPLIED)
        self.assertIsNone(sp_no_subject.hours_completed)  # data beze změny
        log_text = "\n".join(captured.output)
        self.assertIn("manuální triáž", log_text)
        self.assertIn(str(sp_no_subject.pk), log_text)
        self.assertIn(str(sp_no_user.pk), log_text)
        self.assertEqual(PracticeRegistration.objects.count(), 0)

    def test_backfill_is_idempotent(self):
        self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.APPLIED)
        self.make_sp(
            self.owner_student,
            practice=make_practice_no_subject("BL10 idem triáž", self.employer),
            state=StudentPracticeWorkflowState.APPLIED,
        )

        self._run_backfill()
        regs_after_first = PracticeRegistration.objects.count()
        links_after_first = list(StudentPractice.objects.order_by("pk").values_list("pk", "registration_id"))

        self._run_backfill()  # druhý běh nesmí duplikovat ani měnit vazby
        self.assertEqual(PracticeRegistration.objects.count(), regs_after_first)
        self.assertEqual(
            list(StudentPractice.objects.order_by("pk").values_list("pk", "registration_id")),
            links_after_first,
        )

    def test_backfill_links_newly_resolvable_row_to_existing_registration(self):
        """MAJOR-1: dříve triážovaný řádek (opravený subject) se napojí na
        JIŽ EXISTUJÍCÍ registraci stejného klíče — get_or_create, žádný
        IntegrityError, žádný duplikát (dříve: create → padání na unique)."""
        sp_linked = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.APPLIED)
        sp_triage = self.make_sp(
            self.owner_student,
            practice=make_practice_no_subject("BL10 triáž → oprava", self.employer),
            state=StudentPracticeWorkflowState.APPLIED,
        )

        self._run_backfill()
        sp_linked.refresh_from_db()
        sp_triage.refresh_from_db()
        self.assertIsNotNone(sp_linked.registration_id)
        self.assertIsNone(sp_triage.registration_id)  # subject NULL → triáž

        # oprava triáže: řádek dostane předmětovou praxi → nově resolvable
        sp_triage.practice = self.practice_same_subject
        sp_triage.save(update_fields=["practice"])

        self._run_backfill()  # nesmí spadnout na IntegrityError existujícího klíče
        sp_triage.refresh_from_db()
        self.assertEqual(sp_triage.registration_id, sp_linked.registration_id)
        self.assertEqual(PracticeRegistration.objects.count(), 1)  # žádný duplikát

    def test_backfill_mixed_key_partial_retry(self):
        """MAJOR-1: dílčí retry — jeden klíč už existuje (napojeno), druhý
        je nový; jediný běh musí oba správně propojit bez duplikátu."""
        sp_seed = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.APPLIED)
        self._run_backfill()
        sp_seed.refresh_from_db()
        existing_registration = sp_seed.registration

        sp_same_key = self.make_sp(self.owner_student, practice=self.practice_same_subject, state=StudentPracticeWorkflowState.APPLIED)
        sp_new_key = self.make_sp(self.owner_student, practice=self.practice_other_subject, state=StudentPracticeWorkflowState.APPLIED)

        self._run_backfill()
        sp_same_key.refresh_from_db()
        sp_new_key.refresh_from_db()
        self.assertEqual(sp_same_key.registration_id, existing_registration.pk)  # existující klíč
        self.assertNotEqual(sp_new_key.registration_id, existing_registration.pk)  # nový klíč
        self.assertEqual(PracticeRegistration.objects.filter(student=self.owner_student).count(), 2)


class Bl10CountableHoursTests(BL03FixtureMixin, TestCase):
    """Q1-A (I2/I3): countable_hours = jen nestornované vztahy; izolace registrací."""

    @staticmethod
    def _link(sp, registration):
        sp.registration = registration
        sp.save(update_fields=["registration"])

    @staticmethod
    def _set_hours(sp, hours):
        sp.hours_completed = hours
        sp.save(update_fields=["hours_completed"])

    def test_countable_hours_excludes_cancelled(self):
        registration = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year)
        sp_done = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.COMPLETED)
        self._link(sp_done, registration)
        self._set_hours(sp_done, 300)
        sp_cancelled = self.make_sp(
            self.owner_student,
            practice=self.practice_same_subject,
            state=StudentPracticeWorkflowState.ENDED,
            is_cancelled=True,
        )
        self._link(sp_cancelled, registration)
        self._set_hours(sp_cancelled, 200)  # stornované hodiny → do ničeho
        sp_ended = self.make_sp(
            self.owner_student,
            practice=self.make_practice(title="BL10 hodiny 3", subject=self.subject),
            state=StudentPracticeWorkflowState.ENDED,
        )
        self._link(sp_ended, registration)
        self._set_hours(sp_ended, 100)

        self.assertEqual(registration.countable_hours(), 400)
        # porovnatelnost s Subject.min_hours (C21 hodnoty schvalují garanti)
        self.assertLess(registration.countable_hours(), self.subject.min_hours)

    def test_registrations_are_isolated(self):
        """I3: hodiny registrace X nikdy nejsou součtem registrace Y."""
        registration_a = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year)
        registration_b = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject_other, year=date.today().year)
        sp_a = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.ENDED)
        self._link(sp_a, registration_a)
        self._set_hours(sp_a, 500)
        sp_b = self.make_sp(self.owner_student, practice=self.practice_other_subject, state=StudentPracticeWorkflowState.ENDED)
        self._link(sp_b, registration_b)
        self._set_hours(sp_b, 999)

        self.assertEqual(registration_a.countable_hours(), 500)
        self.assertEqual(registration_b.countable_hours(), 999)


class Bl10AllNEvaluationGateTests(BL03FixtureMixin, TestCase):
    """Q3-A (I5): dokončení vyžaduje evaluace VŠECH vztahů registrace."""

    def _link(self, sp, registration):
        sp.registration = registration
        sp.save(update_fields=["registration"])

    def test_completion_requires_all_relationships_evaluated(self):
        registration = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year)
        sp_final = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.ENDED)
        self._link(sp_final, registration)
        sp_sibling = self.make_sp(self.owner_student, practice=self.practice_same_subject, state=StudentPracticeWorkflowState.STARTED)
        self._link(sp_sibling, registration)

        Evaluation.objects.create(student_practice=sp_final, evaluated_by=self.garant)
        self.make_doc(sp_final, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        before = self.sp_snapshot(sp_final)

        # chybí evaluace DRUHÉHO vztahu → dokončení zamítnuto, nulová mutace
        response = self.transition(self.admin, sp_final, StudentPracticeWorkflowState.COMPLETED, reason="BL10 all-N")
        self.assertEqual(response.status_code, 400)
        self.assertIn("VŠECH vztahů registrace", response.data.get("detail", ""))
        self.assertEqual(self.sp_snapshot(sp_final), before)

        # doplnění evaluace druhého vztahu + stornovaný sourozenec NEblokuje (Q1-A)
        Evaluation.objects.create(student_practice=sp_sibling, evaluated_by=self.garant)
        sp_cancelled = self.make_sp(
            self.owner_student,
            practice=self.make_practice(title="BL10 stornovaný sourozenec", subject=self.subject),
            state=StudentPracticeWorkflowState.STARTED,
            is_cancelled=True,
        )
        self._link(sp_cancelled, registration)  # bez evaluace — storno se nepočítá

        response = self.transition(self.admin, sp_final, StudentPracticeWorkflowState.COMPLETED, reason="BL10 all-N ok")
        self.assertEqual(response.status_code, 200)
        sp_final.refresh_from_db()
        self.assertEqual(sp_final.workflow_state, StudentPracticeWorkflowState.COMPLETED)

    def test_single_relationship_gate_unchanged(self):
        registration = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year)
        sp_final = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.ENDED)
        self._link(sp_final, registration)
        Evaluation.objects.create(student_practice=sp_final, evaluated_by=self.garant)
        self.make_doc(sp_final, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)

        response = self.transition(self.admin, sp_final, StudentPracticeWorkflowState.COMPLETED, reason="BL10 N=1")

        self.assertEqual(response.status_code, 200)
        sp_final.refresh_from_db()
        self.assertEqual(sp_final.workflow_state, StudentPracticeWorkflowState.COMPLETED)

    def test_all_n_gate_query_count_is_constant_in_n(self):
        """MAJOR-2: gate nesmí dělat N+1 — počet SQL dotazů je stejný při
        malém i větším počtu sourozenců (Q2-A povoluje neomezené N)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def denial_queries(run_year, n_siblings):
            # unikátní rok per běh → unikátní registrace (unique klíč)
            registration = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=run_year)
            sp_final = self.make_sp(
                self.owner_student,
                practice=self.make_practice(title=f"BL10 q{n_siblings} final", subject=self.subject),
                state=StudentPracticeWorkflowState.ENDED,
            )
            sp_final.registration = registration
            sp_final.save(update_fields=["registration"])
            Evaluation.objects.create(student_practice=sp_final, evaluated_by=self.garant)
            self.make_doc(sp_final, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
            for i in range(n_siblings):
                sibling = self.make_sp(
                    self.owner_student,
                    practice=self.make_practice(title=f"BL10 q{n_siblings} sibling {i}", subject=self.subject),
                    state=StudentPracticeWorkflowState.STARTED,
                )
                sibling.registration = registration
                sibling.save(update_fields=["registration"])

            with CaptureQueriesContext(connection) as ctx:
                with self.assertRaises(ValueError):
                    StudentPracticeService.transition_student_practice_state(
                        sp=sp_final,
                        target_state=StudentPracticeWorkflowState.COMPLETED,
                        actor=self.admin,
                        reason="BL10 query count",
                    )
            sp_final.refresh_from_db()
            self.assertEqual(sp_final.workflow_state, StudentPracticeWorkflowState.ENDED)  # nulová mutace
            return len(ctx.captured_queries)

        denial_queries(2030, 2)  # zahřátí cache (ContentType apod.)
        q_small = denial_queries(2031, 2)
        q_large = denial_queries(2032, 6)
        # O(1): stejný počet dotazů bez ohledu na N
        self.assertEqual(q_large, q_small)


class Bl10C03RegistrationIdentityTests(BL03FixtureMixin, TestCase):
    """C03 + BL-10: blok vázán na plnou identitu registrace (student, subject, year);
    legacy řádky bez registration fallbackují předmětově (fail-closed)."""

    APPLY_URL = "/api/practices/student/apply/"

    def test_pending_on_other_year_does_not_block_current_year(self):
        old_registration = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year - 1)
        sp_old = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.CONTRACTED)
        self._link(sp_old, old_registration)
        StudentPracticeService.submit_cancellation_request(sp_old, self.owner_student, "BL10 starý rok")

        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post(self.APPLY_URL, {"practice": self.practice_same_subject.practice_id}, format="json")

        # jiný rok = jiná registrace → neblokováno
        self.assertEqual(response.status_code, 201)

    def test_pending_on_current_registration_blocks_and_resolve_unblocks(self):
        current = PracticeRegistration.objects.create(student=self.owner_student, subject=self.subject, year=date.today().year)
        sp_cur = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.CONTRACTED)
        self._link(sp_cur, current)
        StudentPracticeService.submit_cancellation_request(sp_cur, self.owner_student, "BL10 aktuální rok")

        self.client.force_authenticate(user=self.owner_student)
        blocked = self.client.post(self.APPLY_URL, {"practice": self.practice_same_subject.practice_id}, format="json")
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(blocked.data))

        self.client.force_authenticate(user=self.garant)
        resolved = self.client.post(
            f"/api/student-practices/{sp_cur.student_practice_id}/resolve-cancellation/",
            {"decision": "reject"},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)

        self.client.force_authenticate(user=self.owner_student)
        allowed = self.client.post(self.APPLY_URL, {"practice": self.practice_same_subject.practice_id}, format="json")
        self.assertEqual(allowed.status_code, 201)

    def test_pending_without_registration_blocks_subject_wide(self):
        """Legacy fallback: řádek bez registration (před backfillem/triáž)
        blokuje předmětově — fail-closed chování zachováno."""
        sp_legacy = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNone(sp_legacy.registration_id)
        StudentPracticeService.submit_cancellation_request(sp_legacy, self.owner_student, "BL10 legacy")

        self.client.force_authenticate(user=self.owner_student)
        blocked = self.client.post(self.APPLY_URL, {"practice": self.practice_same_subject.practice_id}, format="json")
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(blocked.data))

    @staticmethod
    def _link(sp, registration):
        sp.registration = registration
        sp.save(update_fields=["registration"])
