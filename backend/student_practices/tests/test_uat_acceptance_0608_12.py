"""UAT akceptační testy z ``Tests/UAT/UATs.xlsx`` — TC-06, TC-07, TC-08, TC-12.

Pokryté případy
---------------
- 06-01..03  Schválení / zamítnutí obsahu praxe garantem (US-06)
- 07-01..03  Alokace studenta, kapacita a obsazenost (US-07)
- 08-01..02  Potvrzení přijetí smlouvy a eskalace SMLOUVA_PO_TERMINU (US-08)
- 12-01..04  Mentorská evaluace s PDF a její validace (US-12)

Poznámky k odchylkám (UAT očekávání vs. skutečné chování) jsou uvedeny
u konkrétních testů klíčovým slovem ``ODCHYLKA``. Testy jsou psané proti
skutečnému API (Django TestCase + APIClient), nikoli proti UI.
"""

from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from notifications.models import Notification
from rest_framework.test import APIClient
from test_support.contracts import approve_contract_document

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from subject.models import Subject
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import (
    ActionLog,
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class UATFixtureMixin:
    """Syntetická fixture společná pro všechny UAT případy."""

    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(
            department_name="UAT KI",
            department_code="UATKI",
        )
        self.subject = Subject.objects.create(
            subject_name="UAT praxe",
            subject_code="UAT/BOP",
            department=self.department,
        )

        # Organizace (zaměstnavatel praxe)
        self.org_user = OrganizationUser.objects.create(
            email="org@uat-0608.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.pk,
            company_name="UAT Org s.r.o.",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.student = StudentUser.objects.create(
            email="student@uat-0608.test",
            first_name="UAT",
            last_name="Student",
            is_active=True,
        )

        self.garant = ProfessorUser.objects.create_user(
            email="garant@uat-0608.test",
            password="uat-only-password",
            first_name="UAT",
            last_name="Garant",
            is_active=True,
            department=self.department,
            is_garant_praxe=True,
        )
        self.subject.subject_manager_id = self.garant.pk
        self.subject.save(update_fields=["subject_manager"])

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------
    def make_practice(self, *, title="UAT praxe", available_positions=2, external=False):
        return Practice.objects.create(
            title=title,
            description="Syntetická praxe pro UAT 06/07/08/12",
            employer=None if external else self.employer,
            subject=self.subject,
            contact_user=self.org_user,
            is_external=external,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=available_positions,
        )

    def make_sp(
        self,
        user,
        *,
        practice=None,
        state=StudentPracticeWorkflowState.APPLIED,
        approval_status=ApprovalStatus.PENDING,
    ):
        return StudentPractice.objects.create(
            user=user,
            practice=practice or self.make_practice(),
            workflow_state=state,
            approval_status=approval_status,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

    def make_student(self, suffix):
        return StudentUser.objects.create(
            email=f"student-{suffix}@uat-0608.test",
            first_name="UAT",
            last_name=f"Student {suffix}",
            is_active=True,
        )

    def make_content_document(self, sp):
        """Připojí SP nahraný obsahový dokument (nutný pro CONTENT_APPROVED)."""
        doc = UploadedDocument.objects.create(
            document_type=DocumentType.CONTENT,
            status=DocumentStatus.PENDING,
            document=SimpleUploadedFile(
                "obsah_praxe.pdf",
                b"%PDF-1.4 UAT content",
                content_type="application/pdf",
            ),
        )
        sp.content_document = doc
        sp.save(update_fields=["content_document"])
        return doc

    def transition(self, actor, sp, target_state, reason=""):
        self.client.force_authenticate(user=actor)
        payload = {"target_state": target_state.value}
        if reason:
            payload["reason"] = reason
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            payload,
            format="json",
        )


# ======================================================================
# TC-06 — Garant: schválení / zamítnutí obsahu praxe
# ======================================================================


class UAT06ContentApprovalTests(UATFixtureMixin, TestCase):
    """TC-06-01..03 (US-06) — věcné posouzení obsahu praxe garantem."""

    def _content_sp(self):
        external = self.make_practice(title="UAT externí praxe", external=True)
        sp = self.make_sp(
            self.student,
            practice=external,
            state=StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL,
        )
        self.make_content_document(sp)
        return sp

    def test_06_01_approval_sets_content_approved_notifies_student_and_audits(self):
        """TC-06-01: garant schválí obsah → CONTENT_APPROVED.

        Očekávání UAT: stav „Obsah praxe schválen“, student dostane notifikaci,
        systém zaznamená identitu garanta a čas rozhodnutí.
        """
        sp = self._content_sp()

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_APPROVED,
            reason="Obsah odpovídá studijnímu programu.",
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTENT_APPROVED)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                verb="CONTENT_APPROVED",
                object_id=sp.student_practice_id,
            ).exists(),
            "Student měl obdržet notifikaci o schválení obsahu.",
        )

        log = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type=ActionLogType.STATE_TRANSITION,
        ).latest("pk")
        self.assertEqual(log.user_id, self.garant.pk, "Audit musí nést identitu garanta.")
        self.assertIsNotNone(log.action_date, "Audit musí nést čas rozhodnutí.")
        self.assertIn("CONTENT_APPROVED", log.action_description)

    def test_06_02_rejection_sets_content_rejected_and_notifies_with_reason(self):
        """TC-06-02: zamítnutí s důvodem → CONTENT_REJECTED + důvod v notifikaci."""
        sp = self._content_sp()
        reason = "Obsah praxe neodpovídá zaměření oboru."

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_REJECTED,
            reason=reason,
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTENT_REJECTED)

        notification = Notification.objects.filter(
            recipient=self.student,
            verb="CONTENT_REJECTED",
            object_id=sp.student_practice_id,
        ).first()
        self.assertIsNotNone(notification, "Student měl obdržet notifikaci o zamítnutí.")
        self.assertIn(reason, notification.message)

    def test_06_03_rejection_without_reason_is_400_and_state_unchanged(self):
        """TC-06-03: prázdný důvod → HTTP 400 s polem ``reason``, stav beze změny.

        Očekávaný text UAT i aplikace: „Důvod zamítnutí je povinný.“
        """
        sp = self._content_sp()

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_REJECTED,
            reason="",
        )

        self.assertEqual(response.status_code, 400, response.data)
        details = response.data.get("details", response.data)
        self.assertIn("reason", details, f"Odpověď musí obsahovat pole reason: {response.data}")
        self.assertIn("Důvod zamítnutí je povinný.", str(details["reason"]))

        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.student,
                verb="CONTENT_REJECTED",
            ).exists()
        )


# ======================================================================
# TC-07 — Garant: alokace a kapacita
# ======================================================================


class UAT07AllocationTests(UATFixtureMixin, TestCase):
    """TC-07-01..03 (US-07) — alokace studenta, kapacita a obsazenost."""

    def test_07_01_allocation_with_free_capacity_notifies_student_and_organization(self):
        """TC-07-01: 2 místa, 1 obsazené → alokace projde do PRELIMINARY_APPROVED.

        Očekávání UAT: systém ověří volnou kapacitu, stav se přepne na
        „Čeká na schválení organizací“ a notifikaci dostane student i organizace.
        """
        practice = self.make_practice(title="UAT alokace volná", available_positions=2)
        self.make_sp(
            self.make_student("occupied"),
            practice=practice,
            state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
        )
        applicant = self.make_student("applicant")
        sp = self.make_sp(applicant, practice=practice, state=StudentPracticeWorkflowState.APPLIED)

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            reason="Alokace studenta garantem.",
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)

        self.assertTrue(
            Notification.objects.filter(
                recipient=applicant,
                verb="APPLICATION_PRE_APPROVED",
                object_id=sp.student_practice_id,
            ).exists(),
            "Student měl obdržet notifikaci o alokaci.",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.org_user,
                verb="ALLOCATION_ORG",
                object_id=sp.student_practice_id,
            ).exists(),
            "Organizace měla obdržet notifikaci o alokaci (UAT TC-07-01).",
        )

    def test_07_02_allocation_at_full_capacity_returns_capacity_full(self):
        """TC-07-02: plná kapacita → 400/CAPACITY_FULL, alokace neproběhne.

        Očekávání UAT: potvrzení je zablokováno hláškou
        „Kapacita partnera je plně obsazena“ a student není alokován.
        """
        practice = self.make_practice(title="UAT alokace plná", available_positions=2)
        for i in range(2):
            self.make_sp(
                self.make_student(f"full-{i}"),
                practice=practice,
                state=StudentPracticeWorkflowState.CONTRACTED,
                approval_status=ApprovalStatus.APPROVED,
            )
        applicant = self.make_student("full-applicant")
        sp = self.make_sp(applicant, practice=practice, state=StudentPracticeWorkflowState.APPLIED)

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            reason="Alokace při plné kapacitě.",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        self.assertIn("Kapacita partnera je plně obsazena", str(response.data.get("detail", "")))
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)
        self.assertEqual(
            StudentPractice.objects.filter(
                practice=practice,
                workflow_state=StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            ).count(),
            0,
        )

    def test_07_02b_capacity_freed_after_student_cancellation(self):
        """Po stornu obsazeného místa se kapacita uvolní (F-24/D-2)."""
        practice = self.make_practice(title="UAT alokace po stornu", available_positions=1)
        holder = self.make_sp(
            self.make_student("cancel-holder"),
            practice=practice,
            state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
        )
        applicant = self.make_student("cancel-applicant")
        sp = self.make_sp(applicant, practice=practice, state=StudentPracticeWorkflowState.APPLIED)

        self.client.force_authenticate(user=holder.user)
        cancelled = self.client.post(
            f"/api/student-practices/{holder.student_practice_id}/cancel/",
            {"reason": "Student ukončil praxi."},
            format="json",
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        holder.refresh_from_db()
        self.assertTrue(holder.is_cancelled)

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            reason="Alokace po uvolnění místa.",
        )
        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)

    def test_07_02c_ended_and_completed_still_hold_capacity(self):
        """ENDED/COMPLETED zůstávají obsazené — kapacitu neuvolňují (D-2)."""
        for index, state in enumerate((StudentPracticeWorkflowState.ENDED, StudentPracticeWorkflowState.COMPLETED)):
            with self.subTest(state=state):
                practice = self.make_practice(title=f"UAT alokace {state.name}", available_positions=1)
                self.make_sp(
                    self.make_student(f"held-{index}"),
                    practice=practice,
                    state=state,
                    approval_status=ApprovalStatus.APPROVED,
                )
                sp = self.make_sp(
                    self.make_student(f"blocked-{index}"),
                    practice=practice,
                    state=StudentPracticeWorkflowState.APPLIED,
                )

                response = self.transition(
                    self.garant,
                    sp,
                    StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
                    reason="Alokace při plné kapacitě.",
                )

                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
                sp.refresh_from_db()
                self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)

    def test_07_02d_unauthorized_role_gets_403_before_capacity_400(self):
        """Neautorizovaná role → 403 dřív než kapacitní 400 (F-24/D-2)."""
        practice = self.make_practice(title="UAT alokace cizí organizace", available_positions=1)
        self.make_sp(
            self.make_student("foreign-holder"),
            practice=practice,
            state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
        )
        sp = self.make_sp(
            self.make_student("foreign-applicant"),
            practice=practice,
            state=StudentPracticeWorkflowState.APPLIED,
        )

        foreign_org = OrganizationUser.objects.create(
            email="foreign-org@uat-0608.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        foreign_employer = EmployerProfile.objects.create(
            employer_id=foreign_org.pk,
            company_name="UAT cizí organizace s.r.o.",
            approval_status=ApprovalStatus.APPROVED,
        )
        foreign_org.employer_profile = foreign_employer
        foreign_org.save()

        response = self.transition(
            foreign_org,
            sp,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            reason="Neautorizovaná alokace.",
        )

        self.assertEqual(response.status_code, 403, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)

    def test_07_03_occupancy_api_returns_approved_pending_available_as_one_of_two(self):
        """TC-07-03: detail inzerátu vrací obsazenost ve formátu „obsazeno/celkem“.

        Očekávání UAT: 2 místa, 1 obsazené → „1/2“.
        """
        practice = self.make_practice(title="UAT obsazenost", available_positions=2)
        self.make_sp(
            self.make_student("occ-approved"),
            practice=practice,
            state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.make_sp(
            self.make_student("occ-pending"),
            practice=practice,
            state=StudentPracticeWorkflowState.APPLIED,
            approval_status=ApprovalStatus.PENDING,
        )

        self.client.force_authenticate(user=self.garant)
        response = self.client.get(f"/api/practices/student/{practice.practice_id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["approved_applications"], 1)
        self.assertEqual(response.data["pending_applications"], 1)
        self.assertEqual(response.data["available_positions"], 2)
        self.assertEqual(
            f"{response.data['approved_applications']}/{response.data['available_positions']}",
            "1/2",
        )


# ======================================================================
# TC-08 — Garant: smlouva a eskalace
# ======================================================================


class UAT08ContractTests(UATFixtureMixin, TestCase):
    """TC-08-01..02 (US-08) — potvrzení smlouvy a prodlení se zasmluvněním."""

    def test_08_01_confirm_contract_sets_contracted_and_contract_received_date(self):
        """TC-08-01: potvrzení přijetí smlouvy → CONTRACTED + uložené datum.

        A-11: do CONTRACTED se jde jen se schváleným smluvním dokumentem;
        employer osa je v UAT scénáři již potvrzena organizací.

        ODCHYLKA: UAT popisuje ruční zadání data fyzického přijetí smlouvy.
        API ``confirm-contract`` žádné datum v payloadu nepřijímá — uloží
        serverový čas prvního potvrzení do ``contract_received_date``.
        Test proto ověřuje skutečné chování (datum je vyplněné serverem).
        """
        practice = self.make_practice(title="UAT smlouva")
        sp = self.make_sp(
            self.student,
            practice=practice,
            state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )
        StudentPractice.objects.filter(pk=sp.pk).update(employer_approved=True)
        approve_contract_document(sp)
        sp.refresh_from_db()
        self.assertIsNone(sp.contract_received_date)

        self.client.force_authenticate(user=self.garant)
        response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(sp.contract_received_date)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)

    def test_08_02_contract_overdue_flag_and_single_escalation_notification(self):
        """TC-08-02: prodlení → příznak SMLOUVA_PO_TERMINU a jedna eskalace.

        Aplikace exponuje příznak jako ``contract_overdue`` (verb
        ``CONTRACT_OVERDUE``); command ``notify_contract_overdue`` notifikuje
        garanta právě jednou (idempotence přes ``contract_overdue_notified_at``).
        """
        practice = self.make_practice(title="UAT prodlení se smlouvou")
        sp = self.make_sp(
            self.student,
            practice=practice,
            state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )

        # Simulace vstupu do AWAITING_CONTRACT před 8 dny (test_wp09 vzor).
        ActionLogService.log(
            user=None,
            action_type=ActionLogType.STATE_TRANSITION,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=(f"Změna stavu přihlášky ID {sp.student_practice_id}: " "PRELIMINARY_APPROVED -> AWAITING_CONTRACT (bez důvodu)"),
        )
        old = timezone.now() - timedelta(days=8)
        ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type=ActionLogType.STATE_TRANSITION,
        ).update(action_date=old)
        # Command předfiltruje i podle updated_at.
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=old)

        sp.refresh_from_db()
        self.assertTrue(sp.contract_overdue, "Praxe po termínu musí mít příznak prodlení.")

        from django.core.management import call_command

        call_command("notify_contract_overdue")
        call_command("notify_contract_overdue")

        sp.refresh_from_db()
        self.assertIsNotNone(sp.contract_overdue_notified_at)
        notifications = Notification.objects.filter(
            recipient=self.garant,
            verb="CONTRACT_OVERDUE",
            object_id=sp.student_practice_id,
        )
        self.assertEqual(
            notifications.count(),
            1,
            "Garant měl obdržet právě jednu eskalační notifikaci.",
        )


# ======================================================================
# TC-12 — Mentor: evaluace studenta
# ======================================================================


class UAT12EvaluationTests(UATFixtureMixin, TestCase):
    """TC-12-01..04 (US-12) — evaluace mentorem a validace PDF."""

    RATINGS = {
        "expertise_rating": 5,
        "expertise_comment": "Výborná odborná úroveň.",
        "communication_rating": 4,
        "communication_comment": "Dobrá komunikace.",
        "initiative_rating": 5,
        "initiative_comment": "Vysoká iniciativa.",
        "overall_comment": "Doporučuji.",
    }

    def _ended_sp(self):
        return self.make_sp(
            self.student,
            state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
        )

    def _pdf(self, name="hodnoceni_podepsane.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4 UAT evaluation", content_type="application/pdf")

    def _submit(self, sp, extra=None):
        self.client.force_authenticate(user=self.org_user)
        payload = {"student_practice_id": sp.student_practice_id, **self.RATINGS, **(extra or {})}
        return self.client.post("/api/student-practices/evaluations/", payload)

    def test_12_01_evaluation_with_pdf_is_stored_and_notifies_garant(self):
        """TC-12-01: evaluace s PDF → uložena, garant dostane notifikaci."""
        sp = self._ended_sp()

        response = self._submit(sp, {"pdf_file": self._pdf()})

        self.assertEqual(response.status_code, 201, response.data)
        evaluation = Evaluation.objects.get(student_practice=sp)
        self.assertTrue(evaluation.pdf_file.name)
        self.assertTrue(evaluation.pdf_protokol.name, "Měl vzniknout PDF protokol evaluace.")
        self.assertEqual(evaluation.evaluated_by_id, self.org_user.pk)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.garant,
                verb="EVALUATION_SUBMITTED",
            ).exists(),
            "Garant měl obdržet notifikaci o dokončené evaluaci.",
        )

    def test_12_02_evaluation_without_document_is_400(self):
        """TC-12-02: evaluace bez dokumentu → 400, evaluace nevznikne.

        Aplikace vrací text „Nahrání podepsaného hodnotícího archu je povinné“.
        """
        sp = self._ended_sp()

        response = self._submit(sp)

        self.assertEqual(response.status_code, 400, response.data)
        details = response.data.get("details", response.data)
        self.assertIn("pdf_file", details, f"Odpověď musí obsahovat chybu pdf_file: {response.data}")
        self.assertIn("Nahrání podepsaného hodnotícího archu je povinné", str(details["pdf_file"]))
        self.assertFalse(Evaluation.objects.filter(student_practice=sp).exists())

    def test_12_03_evaluation_with_docx_is_400(self):
        """TC-12-03: nepovolený formát .docx → 400, soubor/evaluace není přijata.

        Aplikace vrací validační hlášku „Povolený formát je pouze PDF“.
        """
        sp = self._ended_sp()

        response = self._submit(
            sp,
            {"pdf_file": SimpleUploadedFile("hodnoceni.docx", b"PK\x03\x04 UAT docx")},
        )

        self.assertEqual(response.status_code, 400, response.data)
        details = response.data.get("details", response.data)
        self.assertIn("pdf_file", details, f"Odpověď musí obsahovat chybu pdf_file: {response.data}")
        self.assertIn("Povolený formát je pouze PDF", str(details["pdf_file"]))
        self.assertFalse(Evaluation.objects.filter(student_practice=sp).exists())

    def test_12_04_evaluation_before_ended_is_403_evaluation_not_ended(self):
        """TC-12-04: evaluace před ukončením praxe → 403 EVALUATION_NOT_ENDED.

        Aplikace vrací detail „Evaluace je dostupná až po ukončení praxe“
        s ``error_code`` EVALUATION_NOT_ENDED.
        """
        sp = self.make_sp(
            self.student,
            state=StudentPracticeWorkflowState.CONTRACTED,
            approval_status=ApprovalStatus.APPROVED,
        )

        response = self._submit(sp, {"pdf_file": self._pdf()})

        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data.get("error_code"), "EVALUATION_NOT_ENDED")
        self.assertIn("Evaluace je dostupná až po ukončení praxe", str(response.data.get("detail", "")))
        self.assertFalse(Evaluation.objects.filter(student_practice=sp).exists())
