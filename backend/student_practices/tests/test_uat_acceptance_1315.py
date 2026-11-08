"""UAT akceptační testy z ``Tests/UAT/UATs.xlsx`` — TC-13 (UC-13) a TC-15 (UC-15).

Pokryté případy (docs/test-plan/TESTOVACI_PLAN.md, kap. 5.4 a 5.6)
------------------------------------------------------------------
Standardní cyklus (UC-13):
- 13-03  garant zamítne přihlášku s důvodem → REJECTED
- 13-05  organizace zamítne přihlášku s důvodem → REJECTED
- 13-06  student nahraje smluvní dokument v AWAITING_CONTRACT → AWAITING_DOCUMENTS
- 13-07  garant schválí smluvní dokument → CONTRACTED (obě osy + schválený dokument)
- 13-08  garant zamítne dokument → DOCUMENTS_REJECTED; opravný upload → DOCUMENTS_RESUBMITTED
- 13-10  závěrečné dokumenty schváleny v ENDED → COMPLETED + PDF protokol

Individuální cyklus (UC-15):
- 15-01  odeslání formuláře → AWAITING_CONTENT_APPROVAL
- 15-02  garant schválí obsah → CONTENT_APPROVED
- 15-03  garant zamítne obsah s důvodem → CONTENT_REJECTED; student upraví → zpět do čekání
- 15-04  garant potvrdí fyzické doručení smluv → CONTRACTED (NÁLEZ: blokováno osami)
- 15-06  závěrečné dokumenty → COMPLETED + protokol
- 15-07  zamítnutí závěrečných dokumentů → DOCUMENTS_REJECTED; oprava → DOCUMENTS_RESUBMITTED → ENDED

Odchylky od UAT jsou označené ``ODCHYLKA`` v docstringu konkrétního testu;
skutečný stavový automat je v ``student_practices/services.py``
(``SP_TRANSITIONS`` / ``MANUAL_SP_TRANSITIONS``) a testy se drží jeho chování.
Chybějící funkcionalita je označena ``NÁLEZ`` a test na ni úmyslně selhává.

Testy komunikují přes HTTP API (Django TestCase + APIClient); dokumenty vznikají
v paměti přes ``SimpleUploadedFile``.
"""

from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from notifications.models import Notification
from rest_framework.test import APIClient

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
from users.models import (
    ActionLog,
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)

# Minimální platné PDF (validátor kontroluje pouze signaturu ``%PDF``).
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class UAT1315FixtureMixin:
    """Syntetická fixture společná pro UAT 13/15."""

    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(department_name="UAT13 KI", department_code="U13KI")
        self.subject = Subject.objects.create(
            subject_name="UAT13 praxe",
            subject_code="UAT13/BOP",
            department=self.department,
        )

        # Organizace (zaměstnavatel katalogové praxe).
        self.org_user = OrganizationUser.objects.create(
            email="org@uat-1315.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.pk,
            company_name="UAT13 Org s.r.o.",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.student = StudentUser.objects.create(
            email="student@uat-1315.test",
            first_name="UAT",
            last_name="Student",
            is_active=True,
        )
        self.garant = ProfessorUser.objects.create_user(
            email="garant@uat-1315.test",
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
    # Fixture helpers (vzor: test_bl03_workflow.BL03FixtureMixin)
    # ------------------------------------------------------------------
    def make_practice(
        self,
        *,
        title="UAT13 praxe",
        available_positions=5,
        external=False,
        workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
    ):
        return Practice.objects.create(
            title=title,
            description="Syntetická praxe pro UAT 13/15",
            employer=None if external else self.employer,
            subject=self.subject,
            contact_user=None if external else self.org_user,
            is_external=external,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=workflow_state,
            available_positions=available_positions,
        )

    def make_sp(
        self,
        user,
        *,
        practice=None,
        state=StudentPracticeWorkflowState.APPLIED,
        approval_status=ApprovalStatus.PENDING,
        school_approved=False,
        employer_approved=False,
    ):
        return StudentPractice.objects.create(
            user=user,
            practice=practice or self.make_practice(),
            workflow_state=state,
            approval_status=approval_status,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            year=date.today().year,
            school_approved=school_approved,
            employer_approved=employer_approved,
        )

    def attach_document(self, sp, doc_type, *, status=DocumentStatus.PENDING, with_file=True):
        """Vytvoří dokument v paměti a připojí ho přes FK pole SP (OneToOne)."""
        kwargs = {}
        if with_file:
            kwargs["document"] = SimpleUploadedFile(
                f"uat13_{doc_type.name.lower()}.pdf",
                MINIMAL_PDF,
                content_type="application/pdf",
            )
        doc = UploadedDocument.objects.create(document_type=doc_type, status=status, **kwargs)
        field = {
            DocumentType.CONTRACT: "contract_document",
            DocumentType.CONTENT: "content_document",
            DocumentType.FEEDBACK: "feedback_document",
        }[doc_type]
        setattr(sp, field, doc)
        sp.save(update_fields=[field])
        return doc

    def upload_document(self, doc, actor=None, name="oprava.pdf"):
        self.client.force_authenticate(user=actor or self.student)
        return self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile(name, MINIMAL_PDF, content_type="application/pdf")},
        )

    def review_document(self, doc, actor, status_value, note=""):
        self.client.force_authenticate(user=actor)
        payload = {"status": status_value}
        if note:
            payload["review_note"] = note
        return self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            payload,
            format="json",
        )

    def transition(self, actor, sp, target_state, reason=""):
        self.client.force_authenticate(user=actor)
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": target_state.value, "reason": reason},
            format="json",
        )

    def submit_individual_practice(self):
        """15-01: student odešle formulář individuální (externí) praxe."""
        payload = {
            "employer_name": "UAT13 externí firma",
            "contact_person": "UAT13 Kontakt",
            "contact_email": "kontakt@uat-1315.test",
            "ico": "12345678",
            "address": "UAT13 ulice 1",
            "contact_phone": "+420000000000",
            "external_details_file": SimpleUploadedFile("detaily.pdf", MINIMAL_PDF, content_type="application/pdf"),
            "subject_id": self.subject.subject_id,
            "title": "UAT13 individuální praxe",
            "description": "Syntetické podání individuální praxe",
            "start_date": (date.today() + timedelta(days=10)).strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }
        self.client.force_authenticate(user=self.student)
        response = self.client.post("/api/practices/external/", payload)
        self.assertEqual(response.status_code, 201, response.data)
        return StudentPractice.objects.get(user=self.student, practice_id=response.data["practice_id"])

    def assert_protocol_pdf(self, sp):
        evaluation = Evaluation.objects.get(student_practice=sp)
        self.assertTrue(evaluation.pdf_protokol, "Po přechodu do COMPLETED musí vzniknout PDF protokol.")
        with evaluation.pdf_protokol.open("rb") as handle:
            data = handle.read()
        self.assertTrue(data.startswith(b"%PDF"), "Protokol musí být PDF.")
        return evaluation


# ======================================================================
# UC-13 — Standardní životní cyklus
# ======================================================================


class UAT13StandardCycleTests(UAT1315FixtureMixin, TestCase):
    """TC-13-03, 13-05, 13-06, 13-07, 13-08, 13-10 (UC-13)."""

    def test_13_03_garant_rejects_application_with_reason(self):
        """TC-13-03: garant zamítne přihlášku s důvodem → REJECTED.

        Očekávání UAT: stav „Přihláška na praxi odmítnuta“, důvod je uložen
        a viditelný.

        Důvod se ukládá do ``rejection_reason`` i u běžného zamítnutí
        (vedle auditního záznamu ``ActionLog`` a notifikace studenta).
        """
        sp = self.make_sp(self.student, state=StudentPracticeWorkflowState.APPLIED)
        reason = "Nesplňuje požadavky na odbornou praxi."

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.REJECTED, reason=reason)

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.REJECTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.REJECTED)
        self.assertEqual(sp.workflow_status_label, "Přihláška na praxi odmítnuta")

        # Důvod je vidět v auditu…
        log = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type="STATE_TRANSITION",
        ).latest("pk")
        self.assertIn(reason, log.action_description)

        # …a v notifikaci studenta.
        notification = Notification.objects.filter(
            recipient=self.student,
            verb="APPLICATION_REJECTED",
            object_id=sp.student_practice_id,
        ).first()
        self.assertIsNotNone(notification, "Student měl obdržet notifikaci o zamítnutí.")
        self.assertIn(reason, notification.message)

        # Důvod je nově uložen i v dedikovaném poli.
        self.assertEqual(sp.rejection_reason, reason)

    def test_13_05_organization_rejects_application_with_reason(self):
        """TC-13-05: organizace zamítne přihlášku s důvodem → REJECTED.

        Stejně jako u 13-03 se důvod ukládá do ``rejection_reason`` a je
        dohledatelný v ``ActionLog`` a v notifikaci studenta.
        """
        sp = self.make_sp(self.student, state=StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        reason = "Organizace nemá volnou kapacitu mentorů."

        response = self.transition(self.org_user, sp, StudentPracticeWorkflowState.REJECTED, reason=reason)

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.REJECTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.REJECTED)
        self.assertEqual(sp.workflow_status_label, "Přihláška na praxi odmítnuta")

        log = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type="STATE_TRANSITION",
        ).latest("pk")
        self.assertIn(reason, log.action_description)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                verb="APPLICATION_REJECTED",
                object_id=sp.student_practice_id,
            ).exists()
        )
        self.assertEqual(sp.rejection_reason, reason)

    def test_13_06_contract_upload_auto_transitions_to_awaiting_documents(self):
        """TC-13-06: nahrání smluvního dokumentu v AWAITING_CONTRACT →
        automaticky AWAITING_DOCUMENTS (bez samostatného přechodu)."""
        sp = self.make_sp(self.student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        contract = self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.PENDING)

        response = self.upload_document(contract, actor=self.student, name="smlouva.pdf")

        self.assertEqual(response.status_code, 201, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.assertEqual(sp.workflow_status_label, "Čeká na schválení dokumentů")

    def test_13_07_garant_approves_contract_document_to_contracted(self):
        """TC-13-07: garant schválí smluvní dokument → CONTRACTED.

        Pozn.: UAT označuje krok jako částečně ověřený. Kód vyžaduje současně
        (a) schválený smluvní dokument (A-11) a (b) OBĚ approval osy
        (school + employer) — bez employer osy zůstává SP v AWAITING_DOCUMENTS.
        Employer osa je zde připravena jako předchozí schválení organizací
        (standardní cyklus: org přechod PRELIMINARY_APPROVED → AWAITING_CONTRACT).
        """
        sp = self.make_sp(
            self.student,
            state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
            school_approved=True,
            employer_approved=True,
        )
        contract = self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.PENDING)

        response = self.review_document(contract, self.garant, DocumentStatus.APPROVED.value)

        self.assertEqual(response.status_code, 200, response.data)
        contract.refresh_from_db()
        self.assertEqual(contract.status, DocumentStatus.APPROVED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)
        self.assertEqual(sp.workflow_status_label, "Zasmluvněno")
        self.assertIsNotNone(sp.contract_received_date)

    def test_13_08_garant_rejects_document_then_student_resubmits(self):
        """TC-13-08: garant zamítne dokument s důvodem → DOCUMENTS_REJECTED;
        student nahraje opravený dokument → DOCUMENTS_RESUBMITTED.

        Label ``DOCUMENTS_RESUBMITTED`` je „Opravené dokumenty čekají na
        kontrolu“ (odpovídá UAT stavu „Dokumenty znovu odeslány“).
        """
        sp = self.make_sp(self.student, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        contract = self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.PENDING)
        reason = "Chybí podpis a razítko organizace."

        rejected = self.review_document(contract, self.garant, DocumentStatus.REJECTED.value, note=reason)

        self.assertEqual(rejected.status_code, 200, rejected.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(sp.workflow_status_label, "Dokumenty zamítnuty")
        self.assertEqual(sp.rejection_reason, reason)

        resubmitted = self.upload_document(contract, actor=self.student, name="smlouva_oprava.pdf")

        self.assertEqual(resubmitted.status_code, 201, resubmitted.data)
        sp.refresh_from_db()
        contract.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertEqual(contract.status, DocumentStatus.PENDING)  # upload ≠ approval
        # Label pro DOCUMENTS_RESUBMITTED je nyní definovaný.
        self.assertEqual(sp.workflow_status_label, "Opravené dokumenty čekají na kontrolu")

    def test_13_10_final_documents_approved_in_ended_completes_and_generates_pdf(self):
        """TC-13-10: závěrečné dokumenty schváleny v ENDED → COMPLETED + PDF protokol.

        Kód vyžaduje existující evaluaci a schválený FEEDBACK dokument
        (BE-004/BL-10 Q3) — test je připraví a schválí přes review endpoint.
        """
        sp = self.make_sp(
            self.student,
            state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
        )
        Evaluation.objects.create(student_practice=sp, evaluated_by=self.garant)
        feedback = self.attach_document(sp, DocumentType.FEEDBACK, status=DocumentStatus.PENDING)

        reviewed = self.review_document(feedback, self.garant, DocumentStatus.APPROVED.value)

        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, DocumentStatus.APPROVED)

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.COMPLETED,
            reason="Zápočet udělen po schválení závěrečné dokumentace.",
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.COMPLETED)
        self.assertEqual(sp.progress_status, ProgressStatus.COMPLETED)
        self.assertEqual(sp.workflow_status_label, "Splněno")
        self.assert_protocol_pdf(sp)


# ======================================================================
# UC-15 — Individuální životní cyklus
# ======================================================================


class UAT15IndividualCycleTests(UAT1315FixtureMixin, TestCase):
    """TC-15-01, 15-02, 15-03, 15-04, 15-06, 15-07 (UC-15)."""

    def test_15_01_individual_submission_awaits_content_approval(self):
        """TC-15-01: odeslání formuláře → čekání na schválení obsahu.

        ODCHYLKA: UAT pojmenovává stav „PENDING_CONTENT_APPROVAL“ (stav
        inzerátu). Přihláška na individuální praxi vzniká ve stavu
        ``AWAITING_CONTENT_APPROVAL``; test ověřuje skutečný stav i label.
        """
        sp = self.submit_individual_practice()

        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)
        self.assertEqual(sp.workflow_status_label, "Čeká na schválení obsahu")
        self.assertTrue(sp.practice.is_external)

    def test_15_02_garant_approves_content(self):
        """TC-15-02: garant schválí obsah → CONTENT_APPROVED."""
        sp = self.submit_individual_practice()
        self.attach_document(sp, DocumentType.CONTENT, status=DocumentStatus.PENDING)

        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_APPROVED,
            reason="Obsah odpovídá zaměření oboru.",
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTENT_APPROVED)
        self.assertEqual(sp.workflow_status_label, "Obsah praxe schválen")

    def test_15_03_content_rejection_then_student_resubmits(self):
        """TC-15-03: garant zamítne obsah s důvodem → CONTENT_REJECTED; student
        upraví obsah a odešle znovu → zpět do AWAITING_CONTENT_APPROVAL."""
        sp = self.submit_individual_practice()
        content = self.attach_document(sp, DocumentType.CONTENT, status=DocumentStatus.PENDING)
        reason = "Obsah neodpovídá studijnímu programu."

        rejected = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_REJECTED,
            reason=reason,
        )

        self.assertEqual(rejected.status_code, 200, rejected.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTENT_REJECTED)
        self.assertEqual(sp.workflow_status_label, "Zamítnutí obsahu")
        notification = Notification.objects.filter(
            recipient=self.student,
            verb="CONTENT_REJECTED",
            object_id=sp.student_practice_id,
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn(reason, notification.message)

        # Student upraví obsah (nový upload) a odešle znovu.
        self.assertEqual(self.upload_document(content, actor=self.student, name="obsah_oprava.pdf").status_code, 201)
        resubmitted = self.transition(
            self.student,
            sp,
            StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL,
            reason="Obsah upraven dle připomínek.",
        )

        self.assertEqual(resubmitted.status_code, 200, resubmitted.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)

    def test_15_04_garant_confirms_physical_contract_delivery(self):
        """TC-15-04: garant potvrdí fyzické doručení smluv → CONTRACTED.

        D-1/F-28: u individuální (externí) praxe nemá přihláška
        ``employer_profile`` — partner je doložen garantem schválenou
        smlouvou (A-11), takže stačí školní osa. Druhé potvrzení je
        idempotentní no-op (stav ani datum se nemění).
        """
        sp = self.submit_individual_practice()
        self.attach_document(sp, DocumentType.CONTENT, status=DocumentStatus.PENDING)
        contract = self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.PENDING)

        approved = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.CONTENT_APPROVED,
            reason="Obsah schválen.",
        )
        self.assertEqual(approved.status_code, 200, approved.data)

        # Schválený smluvní dokument je precondition A-11 pro CONTRACTED.
        self.review_document(contract, self.garant, DocumentStatus.APPROVED.value)

        # Přechod do AWAITING_CONTRACT (příprava smlouvy) je v manuálním cyklu povolen.
        to_awaiting = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.AWAITING_CONTRACT,
            reason="Příprava smlouvy.",
        )
        self.assertEqual(to_awaiting.status_code, 200, to_awaiting.data)

        self.client.force_authenticate(user=self.garant)
        confirmed = self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(sp.contract_received_date)
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        contracted_date = sp.contract_received_date
        log_count = ActionLog.objects.count()

        # Idempotence: druhé potvrzení nic nezmění a nezaloguje.
        repeated = self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")
        self.assertEqual(repeated.status_code, 200, repeated.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.contract_received_date, contracted_date)
        self.assertEqual(ActionLog.objects.count(), log_count)

    def test_15_04b_confirm_after_garant_approved_document_advances(self):
        """D-1/F-28 past v idempotenci: garant už schválil dokument
        (``school_approved=True``) a praxe je v ``CONTENT_APPROVED`` — první
        confirm musí přejít do CONTRACTED, nikoli vrátit no-op."""
        external = self.make_practice(title="UAT15 externí po schválení dokumentu", external=True)
        sp = self.make_sp(
            self.student,
            practice=external,
            state=StudentPracticeWorkflowState.CONTENT_APPROVED,
            school_approved=True,
        )
        self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.APPROVED)

        self.client.force_authenticate(user=self.garant)
        url = f"/api/student-practices/{sp.student_practice_id}/confirm-contract/"
        first = self.client.post(url)
        self.assertEqual(first.status_code, 200, first.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(sp.contract_received_date)
        contracted_date = sp.contract_received_date

        second = self.client.post(url)
        self.assertEqual(second.status_code, 200, second.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.contract_received_date, contracted_date)

    def test_15_06_final_documents_complete_individual_practice_with_protocol(self):
        """TC-15-06: závěrečné dokumenty → COMPLETED + PDF protokol.

        Pozn.: ENDED je připraven přímo (krok 15-05 „Ukončeno podle dat“ je
        cron, mimo rozsah tohoto souboru); krok 15-04 je blokován nálezem výše,
        proto se cyklus nepředvádí průchodem z CONTRACTED.
        """
        external = self.make_practice(title="UAT15 ukončená praxe", external=True)
        sp = self.make_sp(
            self.student,
            practice=external,
            state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
        )
        Evaluation.objects.create(student_practice=sp, evaluated_by=self.garant)
        feedback = self.attach_document(sp, DocumentType.FEEDBACK, status=DocumentStatus.PENDING)

        self.assertEqual(
            self.review_document(feedback, self.garant, DocumentStatus.APPROVED.value).status_code,
            200,
        )
        response = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.COMPLETED,
            reason="Závěrečná dokumentace schválena.",
        )

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.COMPLETED)
        self.assertEqual(sp.workflow_status_label, "Splněno")
        self.assert_protocol_pdf(sp)

    def test_15_07_garant_rejects_final_documents_to_documents_rejected(self):
        """TC-15-07 (UAT cesta): garant zamítne závěrečné dokumenty v ENDED →
        DOCUMENTS_REJECTED; student nahraje opravené → DOCUMENTS_RESUBMITTED →
        návrat do ENDED (BDD UC15 AC-LM-07).

        ``process_document_review`` posouvá přihlášku do DOCUMENTS_REJECTED
        i při zamítnutí závěrečného (FEEDBACK) dokumentu ve stavu ENDED, takže
        se spustí plný opravný cyklus: upload → review APPROVED → ENDED.
        """
        external = self.make_practice(title="UAT15 opravný cyklus", external=True)
        sp = self.make_sp(
            self.student,
            practice=external,
            state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
        )
        feedback = self.attach_document(sp, DocumentType.FEEDBACK, status=DocumentStatus.PENDING)
        reason = "Chybí podpis garanta na závěrečném protokolu."

        rejected = self.review_document(feedback, self.garant, DocumentStatus.REJECTED.value, note=reason)

        self.assertEqual(rejected.status_code, 200, rejected.data)
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, DocumentStatus.REJECTED)
        sp.refresh_from_db()
        self.assertEqual(
            sp.workflow_state,
            StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
            "Zamítnutí závěrečného (FEEDBACK) dokumentu v ENDED má převést SP " "do DOCUMENTS_REJECTED a spustit opravný cyklus.",
        )

        resubmitted = self.upload_document(feedback, actor=self.student, name="zaverecny_protokol_oprava.pdf")

        self.assertEqual(resubmitted.status_code, 201, resubmitted.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        # Review musí opravný dokument schválit, jinak je přechod zablokovaný.
        self.assertEqual(
            self.review_document(feedback, self.garant, DocumentStatus.APPROVED.value).status_code,
            200,
        )
        returned = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.ENDED,
            reason="Opravné dokumenty schváleny.",
        )

        self.assertEqual(returned.status_code, 200, returned.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(sp.workflow_status_label, "Ukončeno")

    def test_15_07_actual_repair_loop_works_only_for_contract_document(self):
        """TC-15-07 (skutečný dosažitelný automat): opravná smyčka v ENDED
        funguje jen tehdy, je-li zamítnut dokument typu CONTRACT.

        ODCHYLKA: UAT/BDD mluví o „závěrečných dokumentech“ bez typu; kód
        napojuje přechod ENDED → DOCUMENTS_REJECTED výhradně na CONTRACT
        dokument. Po opravném nahrání navíc přechod do ENDED neprovede upload
        sám — review musí opravný dokument schválit (C19-B/T2c, finding 5)
        a teprve explicitní přechod DOCUMENTS_RESUBMITTED → ENDED vrátí
        praxi do „Ukončeno“.
        """
        external = self.make_practice(title="UAT15 oprava smlouvy", external=True)
        sp = self.make_sp(
            self.student,
            practice=external,
            state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
        )
        contract = self.attach_document(sp, DocumentType.CONTRACT, status=DocumentStatus.PENDING)
        reason = "Chybí podpis garanta na smlouvě."

        rejected = self.review_document(contract, self.garant, DocumentStatus.REJECTED.value, note=reason)

        self.assertEqual(rejected.status_code, 200, rejected.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(sp.rejection_reason, reason)

        resubmitted = self.upload_document(contract, actor=self.student, name="smlouva_oprava.pdf")

        self.assertEqual(resubmitted.status_code, 201, resubmitted.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        self.assertEqual(
            self.review_document(contract, self.garant, DocumentStatus.APPROVED.value).status_code,
            200,
        )
        # Nová brána opravného cyklu vyžaduje schválený závěrečný (FEEDBACK)
        # dokument — doplníme ho, aby návrat do ENDED odpovídal realitě.
        self.attach_document(sp, DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        returned = self.transition(
            self.garant,
            sp,
            StudentPracticeWorkflowState.ENDED,
            reason="Opravné dokumenty schváleny.",
        )

        self.assertEqual(returned.status_code, 200, returned.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(sp.workflow_status_label, "Ukončeno")
