"""BL-03 — workflow/allocation regression tests (audit BE-004/005/013, C01–C21 + T2a–T2d).

Pokryté položky zadání:
1. Atomický student create+apply (BE-013) — právě jeden Practice + jedna SP nebo čistá chyba.
2. Kapacita na VŠECH cestách do CONTRACTED (BE-005) — T2a počítací množina,
   stornované/axis-pending se NEPOČÍTAJÍ, guard na generic/review/confirm/apply cestách.
3. Completion gate (BE-004, BL-10 Q3) — ENDED→COMPLETED jen se schválenými hodnotícími podklady.
4. Cancellation request flow (A-12, C03-A + BE-014) — okamžité storno studentem, blok
   nové žádosti do vzetí na vědomí garantem, nevratnost.
5. Opravná smyčka (C19-B/T2c) — DOCUMENTS_RESUBMITTED review-pending, review
   rozhoduje, terminální zamítnutí jen admin + důvod, BE-015 deny na nových hranách.
6. Auto-close jen manuálně (C20-A) — kapacitní auto-close guardován, TIME cutoff odděleně.
7. Confirm-contract T2b — zdrojové stavy + idempotence stejné osy bez duplicitní notifikace.

Vše syntetické; běh izolovanými test settings (audit verification wrapper).
"""

import threading
from datetime import date, timedelta
from io import StringIO
from unittest import mock
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase
from notifications.models import Notification
from rest_framework.test import APIClient
from test_support.contracts import approve_contract_document

from department.models import Department
from practices.models import (
    ApplicationClosureReason,
    Practice,
    PracticeWorkflowState,
    ProgressStatus,
)
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    EmployerInvitation,
    EmployerInvitationStatus,
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from student_practices.services import (
    AxesIncompleteError,
    StudentPracticeService,
    _check_contract_capacity,
    record_own_approval_axis,
)
from subject.models import Subject
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class BL03FixtureMixin:
    """Sdílená syntetická fixture pro BL-03 testy."""

    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(department_name="BL03 KI", department_code="CKI")
        self.other_department = Department.objects.create(department_name="BL03 MA", department_code="CMA")
        self.subject = Subject.objects.create(subject_name="BL03 praxe", subject_code="CBL03/BOP", department=self.department)
        self.subject_other = Subject.objects.create(subject_name="BL03 jiný předmět", subject_code="CBL03B/BOP", department=self.department)

        self.org_user = OrganizationUser.objects.create(
            email="owner-org@bl03.test", is_active=True, organization_role=OrganizationRole.OWNER
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.pk, company_name="BL03 Org", approval_status=ApprovalStatus.APPROVED
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.foreign_org = OrganizationUser.objects.create(
            email="foreign-org@bl03.test", is_active=True, organization_role=OrganizationRole.OWNER
        )
        self.foreign_employer = EmployerProfile.objects.create(
            employer_id=self.foreign_org.pk, company_name="BL03 Foreign Org", approval_status=ApprovalStatus.APPROVED
        )
        self.foreign_org.employer_profile = self.foreign_employer
        self.foreign_org.save()

        self.owner_student = StudentUser.objects.create(
            email="owner-student@bl03.test", first_name="BL03", last_name="Owner", is_active=True
        )
        self.other_student = StudentUser.objects.create(
            email="other-student@bl03.test", first_name="BL03", last_name="Other", is_active=True
        )
        self.foreign_student = StudentUser.objects.create(
            email="foreign-student@bl03.test", first_name="BL03", last_name="Foreign", is_active=True
        )

        self.garant = ProfessorUser.objects.create_user(
            email="garant@bl03.test",
            password="bl03-only-password",
            first_name="BL03",
            last_name="Garant",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.foreign_professor = ProfessorUser.objects.create_user(
            email="foreign-prof@bl03.test",
            password="bl03-only-password",
            first_name="BL03",
            last_name="ForeignProf",
            is_active=True,
            department=self.other_department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.admin = get_user_model().objects.create_superuser(email="admin@bl03.test", password="bl03-only-password")

        self.subject.subject_manager_id = self.garant.pk
        self.subject.save(update_fields=["subject_manager"])

        # Standardní praxe (kapacita volitelná) + druhá praxe téhož předmětu
        # + praxe jiného předmětu (C03-A „stejná registrace“ ≈ student+subject).
        self.practice = self.make_practice(available_positions=10)
        self.practice_same_subject = self.make_practice(title="BL03 praxe (též subject)", available_positions=10)
        self.practice_other_subject = self.make_practice(
            title="BL03 praxe (jiný subject)", subject=self.subject_other, available_positions=10
        )

    def make_practice(
        self,
        *,
        title="BL03 praxe",
        available_positions=10,
        external=False,
        subject=None,
        workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        start_days=10,
    ):
        return Practice.objects.create(
            title=title,
            description="Syntetická praxe pro BL03 testy",
            employer=None if external else self.employer,
            subject=subject or self.subject,
            contact_user=self.org_user,
            is_external=external,
            start_date=date.today() + timedelta(days=start_days),
            end_date=date.today() + timedelta(days=start_days + 30),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=workflow_state,
            available_positions=available_positions,
        )

    def make_sp(self, user, *, practice=None, state=StudentPracticeWorkflowState.APPLIED, is_cancelled=False):
        return StudentPractice.objects.create(
            user=user,
            practice=practice or self.practice,
            workflow_state=state,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_cancelled=is_cancelled,
        )

    def make_doc(self, sp, *, doc_type=DocumentType.CONTRACT, status=DocumentStatus.PENDING):
        """Vytvoří dokument a připojí ho přes FK pole SP (student_practice
        je odvozený reverse-OneToOne property, nedá se assignovat)."""
        doc = UploadedDocument.objects.create(document_type=doc_type, status=status)
        sp_field = {
            DocumentType.CONTRACT: "contract_document",
            DocumentType.CONTENT: "content_document",
            DocumentType.FEEDBACK: "feedback_document",
        }[doc_type]
        setattr(sp, sp_field, doc)
        sp.save(update_fields=[sp_field])
        return doc

    def sp_snapshot(self, sp):
        sp.refresh_from_db()
        return {
            "workflow_state": sp.workflow_state,
            "approval_status": sp.approval_status,
            "progress_status": sp.progress_status,
            "is_cancelled": sp.is_cancelled,
            "school_approved": sp.school_approved,
            "employer_approved": sp.employer_approved,
        }

    def transition(self, actor, sp, target_state, reason="BL03 synthetic"):
        self.client.force_authenticate(user=actor)
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": target_state.value, "reason": reason},
            format="json",
        )


# ===================================================================
# 1) BE-013 — atomický student create+apply
# ===================================================================


class Bl03ExternalAtomicityTests(BL03FixtureMixin, TestCase):
    def _payload(self):
        return {
            "employer_name": "BL03 Synthetic External",
            "contact_person": "BL03 Contact",
            "contact_email": "contact@bl03.test",
            "ico": "12345678",
            "address": "BL03 address",
            "contact_phone": "+420000000000",
            "external_details_file": SimpleUploadedFile("bl03.pdf", b"%PDF-1.4 bl03", content_type="application/pdf"),
            "subject_id": self.subject.subject_id,
            "title": "BL03 individuální praxe",
            "description": "Syntetické BL03 podání",
            "start_date": (date.today() + timedelta(days=10)).strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }

    def test_student_external_create_creates_practice_and_sp_atomically(self):
        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post("/api/practices/external/", self._payload())

        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("warning", response.data)
        practice = Practice.objects.get(pk=response.data["practice_id"])
        sps = StudentPractice.objects.filter(user=self.owner_student, practice=practice)
        self.assertEqual(sps.count(), 1)
        sp = sps.get()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL)
        # BE-013 closure: subject MUSÍ být persistován (baseline ReadOnlyField ho odhazoval)
        self.assertEqual(practice.subject_id, self.subject.subject_id)
        # BE-013 closure: kompletní datumový pár (apply vyžaduje end_date)
        self.assertIsNotNone(practice.start_date)
        self.assertIsNotNone(practice.end_date)

    def test_failed_apply_rolls_back_practice_and_returns_400(self):
        """Žádný 201-warning bez SP; žádný osiřelý Practice/ExternalEmployerInfo."""
        from practices.models import ExternalEmployerInfo

        self.client.force_authenticate(user=self.owner_student)
        with patch(
            "practices.services.PracticeService.apply_student_practice",
            side_effect=ValueError("SIMULATED_APPLY_FAILURE"),
        ):
            response = self.client.post("/api/practices/external/", self._payload())

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("warning", response.data)
        self.assertIn("detail", response.data)
        self.assertEqual(Practice.objects.filter(title="BL03 individuální praxe").count(), 0)
        self.assertEqual(StudentPractice.objects.filter(user=self.owner_student).count(), 0)
        self.assertEqual(ExternalEmployerInfo.objects.filter(name="BL03 Synthetic External").count(), 0)

    def test_late_failure_emits_no_outbound_notification(self):
        """F7: pozdější chyba v transakci → rollback, žádná odchozí pošta,
        nulové počty Practice/SP/ExternalEmployerInfo/Notification."""
        fail_al = MagicMock()
        fail_al.log.side_effect = ValueError("SIMULATED_LATE_FAILURE")

        self.client.force_authenticate(user=self.owner_student)
        with self.captureOnCommitCallbacks(execute=True):
            with patch("practices.services.ActionLogService", fail_al):
                response = self.client.post("/api/practices/external/", self._payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("SIMULATED_LATE_FAILURE", str(response.data))
        # rollback: žádné DB objekty, žádné notifikační řádky, žádná pošta
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Practice.objects.filter(title="BL03 individuální praxe").count(), 0)
        self.assertEqual(StudentPractice.objects.filter(user=self.owner_student).count(), 0)
        from practices.models import ExternalEmployerInfo

        self.assertEqual(ExternalEmployerInfo.objects.filter(name="BL03 Synthetic External").count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_success_sends_outbound_email_after_commit(self):
        """F7 kontrolní: při úspěchu jsou odložené e-maily po commitu odeslány."""
        self.client.force_authenticate(user=self.owner_student)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/practices/external/", self._payload())

        self.assertEqual(response.status_code, 201, response.data)
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertEqual(Practice.objects.filter(title="BL03 individuální praxe").count(), 1)


# ===================================================================
# 2) BE-005 / T2a — kapacita na všech cestách
# ===================================================================


class Bl03CapacityMatrixTests(BL03FixtureMixin, TestCase):
    def _student(self, i):
        return StudentUser.objects.create(email=f"matrix-student-{i}@bl03.test", first_name="BL03", last_name=f"M{i}", is_active=True)

    def test_t2a_counting_matrix_ignores_cancelled_and_pending(self):
        """T2a: CONTRACTED/STARTED/ENDED/COMPLETED se počítají; stornované
        a axis-pending (AWAITING_*, jednoosé) NE."""
        practice = self.make_practice(title="BL03 matrix", available_positions=4)
        states_counted = [
            StudentPracticeWorkflowState.CONTRACTED,
            StudentPracticeWorkflowState.STARTED,
            StudentPracticeWorkflowState.ENDED,
            StudentPracticeWorkflowState.COMPLETED,
        ]
        for i, st in enumerate(states_counted):
            self.make_sp(self._student(i), practice=practice, state=st)

        # nepočítané: stornovaný CONTRACTED + pending AWAITING_CONTRACT +
        # axis-pending (AWAITING_DOCUMENTS s jednou schvalovací osou)
        cancelled = self.make_sp(self._student(4), practice=practice, state=StudentPracticeWorkflowState.CONTRACTED, is_cancelled=True)
        self.make_sp(self._student(5), practice=practice, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        pending = self.make_sp(self._student(6), practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        pending.school_approved = True  # jedna osa — axis-pending, NEPOČÍTÁ SE
        pending.save(update_fields=["school_approved"])

        # Pozorováno: jen 4 počítaná umístění (cancelled/pending vyřazeny)
        counted = StudentPractice.objects.filter(
            practice=practice,
            is_cancelled=False,
            workflow_state__in=states_counted,
        ).count()
        self.assertEqual(counted, 4)
        with self.assertRaises(ValueError) as cm:
            _check_contract_capacity(practice)
        self.assertEqual(str(cm.exception), "CAPACITY_FULL")

        # Stornování jednoho umístění → kapacita se uvolní (cancelled NEPOČÍTÁ)
        first_contracted = StudentPractice.objects.filter(
            practice=practice, is_cancelled=False, workflow_state=StudentPracticeWorkflowState.CONTRACTED
        ).first()
        self.assertIsNotNone(first_contracted)
        first_contracted.is_cancelled = True
        first_contracted.save(update_fields=["is_cancelled"])
        _check_contract_capacity(practice)  # nezvedá výjimku
        _ = cancelled

    def test_generic_awaiting_documents_to_contracted_blocked_at_capacity(self):
        """BE-005 path: generic AWAITING_DOCUMENTS→CONTRACTED podléhá kapacitě."""
        practice = self.make_practice(title="BL03 cap-AD", available_positions=1)
        self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.CONTRACTED)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        # T1 brána: obě osy musí držet, aby test měřil KAPACITU (ne osy)
        StudentPractice.objects.filter(pk=sp.pk).update(employer_approved=True)
        approve_contract_document(sp)  # A-11: do CONTRACTED jen se schválenou smlouvou
        sp.refresh_from_db()
        before = self.sp_snapshot(sp)

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.CONTRACTED)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_generic_content_approved_to_contracted_blocked_at_capacity(self):
        """BE-005 path: externí CONTENT_APPROVED→CONTRACTED podléhá kapacitě."""
        external = self.make_practice(title="BL03 cap-EXT", available_positions=1, external=True)
        self.make_sp(self.other_student, practice=external, state=StudentPracticeWorkflowState.CONTRACTED)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.CONTENT_APPROVED)
        # T1 brána: obě osy musí držet, aby test měřil KAPACITU (ne osy)
        StudentPractice.objects.filter(pk=sp.pk).update(employer_approved=True)
        approve_contract_document(sp)  # A-11: do CONTRACTED jen se schválenou smlouvou
        sp.refresh_from_db()
        before = self.sp_snapshot(sp)

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.CONTRACTED)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_document_review_approval_blocked_at_capacity(self):
        """BE-005 path (HTTP): review schválí smlouvu, ale při plné kapacitě
        se SP nepřevede na CONTRACTED (tichý skip, žádná mutace stavu)."""
        practice = self.make_practice(title="BL03 cap-review", available_positions=1)
        self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.CONTRACTED)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        doc = self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.PENDING)
        # T1 brána: employer osa musí držet, aby test měřil KAPACITU (ne osy)
        StudentPractice.objects.filter(pk=sp.pk).update(employer_approved=True)
        sp.refresh_from_db()
        before = self.sp_snapshot(sp)

        self.client.force_authenticate(user=self.garant)
        response = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}", {"status": DocumentStatus.APPROVED.value}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.APPROVED)  # review proběhl
        self.assertEqual(self.sp_snapshot(sp), before)  # ALE alokace blokována
        self.assertEqual(
            StudentPractice.objects.filter(practice=practice, workflow_state=StudentPracticeWorkflowState.CONTRACTED).count(),
            1,
        )

    def test_confirm_contract_capacity_guard_invoked(self):
        """Confirm-contract cesta volí kapacitní guard (select_for_update)."""
        practice = self.make_practice(title="BL03 cap-confirm", available_positions=5)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        # kapacita se kontroluje až po osách a schválené smlouvě (osa → dokument → kapacita)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True)
        sp.refresh_from_db()
        approve_contract_document(sp)

        with patch(
            "student_practices.services._check_contract_capacity",
            wraps=_check_contract_capacity,
        ) as spy:
            self.client.force_authenticate(user=self.org_user)
            response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(spy.called)

    def test_apply_blocked_when_placements_full(self):
        """T2a apply guard: umístění (CONTRACTED) plní kapacitu → nová žádost 400."""
        practice = self.make_practice(title="BL03 cap-apply", available_positions=1)
        self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.CONTRACTED)

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.post("/api/practices/student/apply/", {"practice": practice.practice_id}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")

    def test_pending_application_does_not_consume_placement(self):
        """Opravený oracle T2a: axis-pending přihláška NEKONZUMUJE místo —
        druhá žádost při volné kapacitě umístění projde."""
        practice = self.make_practice(title="BL03 pending-apply", available_positions=1)
        self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.APPLIED)

        self.client.force_authenticate(user=self.other_student)
        response = self.client.post("/api/practices/student/apply/", {"practice": practice.practice_id}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_cancelled_placement_does_not_consume_placement(self):
        """T2a: stornované umístění se NEPOČÍTÁ — kapacita se uvolní."""
        practice = self.make_practice(title="BL03 cancelled-cap", available_positions=1)
        sp = self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.CONTRACTED)

        # Plná → žádost odmítnuta
        self.client.force_authenticate(user=self.foreign_student)
        url = "/api/practices/student/apply/"
        denied = self.client.post(url, {"practice": practice.practice_id}, format="json")
        self.assertEqual(denied.status_code, 400)

        # Storno umístění → kapacita volná
        StudentPracticeService.cancel_student_practice(sp, self.garant, "BL03 storno umístění")
        allowed = self.client.post(url, {"practice": practice.practice_id}, format="json")
        self.assertEqual(allowed.status_code, 201)


# ===================================================================
# Finding 1 — T1 ústřední brána do CONTRACTED na každé HTTP cestě
# ===================================================================


class Bl03T1CentralGateTests(BL03FixtureMixin, TestCase):
    def test_generic_contracted_transition_requires_both_axes_http(self):
        """F1 generic: škola bez employer osy → 400 AXES_INCOMPLETE,
        nulová mutace (stav/obě osy/ActionLog/Notification)."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.CONTRACTED)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "AXES_INCOMPLETE")
        self.assertIn("employer", response.data.get("detail", ""))
        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(before["school_approved"], False)
        self.assertEqual(before["employer_approved"], False)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_document_review_advance_requires_both_axes_http(self):
        """F1 document: review smlouvy bez employer osy → dokument schválen,
        ALE SP zůstává ve AWAITING_DOCUMENTS, employer_approved=False,
         žádná ALLOCATION/CONTRACTED notifikace."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        doc = self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.PENDING)

        self.client.force_authenticate(user=self.garant)
        response = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )

        self.assertEqual(response.status_code, 200)  # review proběhl
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.APPROVED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)  # nepostupuje
        self.assertFalse(sp.employer_approved)  # cizí osa NE nastavena
        self.assertTrue(sp.school_approved)  # vlastní (školní) osa zapsána
        # žádná notifikace tvrdící CONTRACTED/alokaci
        self.assertFalse(
            Notification.objects.filter(
                verb__in=("APPLICATION_CONTRACTED", "ALLOCATION_ORG"),
            ).exists()
        )

    def test_external_contracted_transition_requires_school_axis_and_contract_http(self):
        """F1/D-1 external: CONTENT_APPROVED→CONTRACTED stačí školní osa
        a schválená smlouva (A-11); employer osa se nevyžaduje."""
        external = self.make_practice(title="BL03 T1-ext", external=True)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.CONTENT_APPROVED)
        self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.APPROVED)

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.CONTRACTED)

        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        self.assertIsNotNone(sp.contract_received_date)


# ===================================================================
# 3) BE-004 / BL-10 Q3 — completion gate
# ===================================================================


class Bl03CompletionGateTests(BL03FixtureMixin, TestCase):
    def _complete(self, sp, actor=None):
        return self.transition(actor or self.admin, sp, StudentPracticeWorkflowState.COMPLETED, reason="BL03 dokončení")

    def _attach_feedback(self, sp, status):
        return self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=status)

    def test_completion_without_evaluation_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.ENDED)
        before = self.sp_snapshot(sp)

        response = self._complete(sp)

        self.assertEqual(response.status_code, 400)
        self.assertIn("evaluace", response.data.get("detail", "").lower())
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_completion_with_unapproved_feedback_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.ENDED)
        Evaluation.objects.create(student_practice=sp, evaluated_by=self.garant)
        self._attach_feedback(sp, DocumentStatus.PENDING)
        before = self.sp_snapshot(sp)

        response = self._complete(sp)

        self.assertEqual(response.status_code, 400)
        self.assertIn("FEEDBACK", response.data.get("detail", ""))
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_completion_with_rejected_feedback_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.ENDED)
        Evaluation.objects.create(student_practice=sp, evaluated_by=self.garant)
        self._attach_feedback(sp, DocumentStatus.REJECTED)
        before = self.sp_snapshot(sp)

        response = self._complete(sp)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_completion_with_approved_evaluation_allowed(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.ENDED)
        Evaluation.objects.create(student_practice=sp, evaluated_by=self.garant)
        self._attach_feedback(sp, DocumentStatus.APPROVED)

        response = self._complete(sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.COMPLETED)
        self.assertEqual(sp.progress_status, ProgressStatus.COMPLETED)


# ===================================================================
# 4) A-12 / C03-A / BE-014 — storno studentem
# ===================================================================


class Bl03CancellationRequestTests(BL03FixtureMixin, TestCase):
    """A-12: okamžité storno studentem (BDD UC05 AC-01…05, UAT TC-05-xx, AC-LC-09)."""

    def _submit_request(self, sp, actor, reason="BL03 synthetic request"):
        self.client.force_authenticate(user=actor)
        return self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/cancel/",
            {"reason": reason},
            format="json",
        )

    def _resolve(self, sp, resolver):
        self.client.force_authenticate(user=resolver)
        return self.client.post(f"/api/student-practices/{sp.student_practice_id}/resolve-cancellation/", {}, format="json")

    def test_owner_student_cancels_immediately_from_contracted(self):
        """AC-02: praxe je po odeslání okamžitě Stornováno, důvod i původní stav se uloží."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)

        response = self._submit_request(sp, self.owner_student)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.is_cancelled)
        self.assertEqual(sp.cancelled_from_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.cancellation_reason, "BL03 synthetic request")
        self.assertIsNotNone(sp.cancellation_requested_at)
        self.assertIsNone(sp.cancellation_resolved_at)

    def test_cancellation_frees_capacity(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)
        occupied = StudentPractice.objects.filter(
            practice=sp.practice, is_cancelled=False, workflow_state=StudentPracticeWorkflowState.CONTRACTED
        ).count()
        self.assertEqual(occupied, 0)

    def test_reason_is_required(self):
        """AC-01."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        response = self._submit_request(sp, self.owner_student, reason="   ")
        self.assertEqual(response.status_code, 400)
        sp.refresh_from_db()
        self.assertFalse(sp.is_cancelled)

    def test_foreign_student_cancel_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        before = self.sp_snapshot(sp)

        response = self._submit_request(sp, self.foreign_student, reason="foreign attempt")

        self.assertEqual(response.status_code, 403)
        sp.refresh_from_db()
        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertIsNone(sp.cancellation_requested_at)

    def test_cancellation_is_irreversible_and_not_repeatable(self):
        """RF-16: druhé storno téže praxe se odmítne a stav se nemění."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)

        response = self._submit_request(sp, self.owner_student, reason="druhé storno")

        self.assertIn(response.status_code, (400, 403))
        sp.refresh_from_db()
        self.assertEqual(sp.cancellation_reason, "BL03 synthetic request")

    def test_completed_and_rejected_cannot_be_cancelled(self):
        for state in (StudentPracticeWorkflowState.COMPLETED, StudentPracticeWorkflowState.REJECTED):
            with self.subTest(state=state.name):
                StudentPractice.objects.filter(user=self.owner_student).delete()
                sp = self.make_sp(self.owner_student, state=state)
                with self.assertRaises(ValueError):
                    StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "pozdě")
                sp.refresh_from_db()
                self.assertFalse(sp.is_cancelled)
                self.assertIsNone(sp.cancellation_requested_at)

    def test_garant_is_notified_and_audit_logged(self):
        """AC-03 a AC-05: notifikace garantovi (po commitu) a audit s datem a důvodem."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        with mock.patch("student_practices.services.NotificationService.notify_garant_cancellation") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)
        notify.assert_called_once()
        log = ActionLog.objects.filter(object_type="StudentPractice", object_id=sp.student_practice_id).latest("pk")
        self.assertIn("BL03 synthetic request", log.action_description)
        self.assertIn("CONTRACTED", log.action_description)

    def test_cancellation_blocks_any_new_application_until_resolved(self):
        """AC-04: blokace trvá, dokud garant storno nevezme na vědomí; platí napříč předměty."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)

        self.client.force_authenticate(user=self.owner_student)
        for practice in (self.practice_same_subject, self.practice_other_subject):
            blocked = self.client.post("/api/practices/student/apply/", {"practice": practice.practice_id}, format="json")
            self.assertEqual(blocked.status_code, 400)
            self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(blocked.data))
        reapply = self.client.post(f"/api/student-practices/reapply/{self.practice_same_subject.practice_id}/", {}, format="json")
        self.assertEqual(reapply.status_code, 400)

        self.assertEqual(self._resolve(sp, self.garant).status_code, 200)

        self.client.force_authenticate(user=self.owner_student)
        allowed = self.client.post("/api/practices/student/apply/", {"practice": self.practice_same_subject.practice_id}, format="json")
        self.assertEqual(allowed.status_code, 201)

    def test_resolve_only_acknowledges_and_keeps_cancellation(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)

        response = self._resolve(sp, self.garant)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.is_cancelled)
        self.assertEqual(sp.cancelled_by_id, self.owner_student.pk)
        self.assertIsNotNone(sp.cancellation_resolved_at)
        second = self._resolve(sp, self.garant)
        self.assertEqual(second.status_code, 400)
        self.assertIn("již vyřešeno", str(second.data))

    def test_resolve_requires_cancelled_practice(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        response = self._resolve(sp, self.garant)
        self.assertEqual(response.status_code, 400)

    def test_foreign_resolver_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self._submit_request(sp, self.owner_student).status_code, 200)

        response = self._resolve(sp, self.foreign_professor)

        self.assertEqual(response.status_code, 403)
        sp.refresh_from_db()
        self.assertIsNone(sp.cancellation_resolved_at)


# ===================================================================
# 5) C19-B / T2c — opravná smyčka dokumentů
# ===================================================================


class Bl03RepairLoopTests(BL03FixtureMixin, TestCase):
    def _dr_sp(self, practice=None):
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        doc = self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.REJECTED)
        return sp, doc

    def _upload(self, doc, actor=None):
        self.client.force_authenticate(user=actor or self.owner_student)
        return self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile("repaired.pdf", b"%PDF-1.4 bl03 repair", content_type="application/pdf")},
        )

    def test_resubmit_upload_enters_review_pending(self):
        """C19-B: upload opravy → EXPLICITNÍ review-pending; upload ≠ approval."""
        sp, doc = self._dr_sp()
        before = self.sp_snapshot(sp)
        self.assertEqual(before["workflow_state"], StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

        response = self._upload(doc)

        self.assertEqual(response.status_code, 201)
        sp.refresh_from_db()
        # upload ≠ approval: review-pending, NIKDY přímé ENDED (C19-B)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.PENDING)

    def test_reviewer_approves_final_docs_to_ended(self):
        sp, doc = self._dr_sp()
        self.assertEqual(self._upload(doc).status_code, 201)
        # finding 5: nejdřív review schválí opravený dokument (state13 precondition)
        self.client.force_authenticate(user=self.garant)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.APPROVED)

        # Nová brána opravného cyklu vyžaduje schválený FEEDBACK dokument.
        self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED, reason="review schvaluje")

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

    def test_reviewer_rejects_back_to_documents_rejected(self):
        sp, doc = self._dr_sp()
        self.assertEqual(self._upload(doc).status_code, 201)

        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.DOCUMENTS_REJECTED, reason="review zamita")

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

    def test_repair_loop_is_unlimited(self):
        """Dvě plná kola oprav → review pokaždé rozhodne; smyčka nekončí."""
        sp, doc = self._dr_sp()
        for round_no in range(2):
            self.assertEqual(self._upload(doc).status_code, 201)
            sp.refresh_from_db()
            self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
            # Rejection must come from review: a generic state transition does
            # not mark the currently pending replacement document rejected.
            self.client.force_authenticate(user=self.garant)
            response = self.client.patch(
                f"/api/student-practices/review-document/{doc.pk}",
                {"status": DocumentStatus.REJECTED.value, "review_note": f"kolo {round_no}"},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            sp.refresh_from_db()
            self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        # třetí kolo končí review souhlasem (finding 5: nejdřív schválit doklad)
        self.assertEqual(self._upload(doc).status_code, 201)
        self.client.force_authenticate(user=self.garant)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        # Nová brána opravného cyklu vyžaduje schválený FEEDBACK dokument.
        self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        response = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

    def test_terminal_rejection_requires_admin_with_reason(self):
        """T2c/R44: terminální REJECTED z opravného cyklu = jen admin + důvod."""
        sp, doc = self._dr_sp()
        before = self.sp_snapshot(sp)

        # 1) garant (ne-admin) → odmítnuto
        denied = self.transition(self.garant, sp, StudentPracticeWorkflowState.REJECTED, reason="garant se pokusil")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.sp_snapshot(sp), before)

        # 2) admin bez důvodu → 400
        no_reason = self.transition(self.admin, sp, StudentPracticeWorkflowState.REJECTED, reason="")
        self.assertEqual(no_reason.status_code, 400)
        self.assertEqual(self.sp_snapshot(sp), before)

        # 3) admin + důvod → 200 terminální zamítnutí
        ok = self.transition(self.admin, sp, StudentPracticeWorkflowState.REJECTED, reason="BL03 terminální důvod")
        self.assertEqual(ok.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.REJECTED)

    def test_terminal_rejection_from_review_pending_admin_only(self):
        sp, doc = self._dr_sp()
        self.assertEqual(self._upload(doc).status_code, 201)
        before = self.sp_snapshot(sp)

        denied = self.transition(self.garant, sp, StudentPracticeWorkflowState.REJECTED, reason="ne admin")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.sp_snapshot(sp), before)

    def test_foreign_denied_on_review_pending_edges(self):
        """BE-015: cizí aktér odmítnut na každé nové hraně bez mutace."""
        sp, doc = self._dr_sp()

        # cizí student: generic DR → DOCUMENTS_RESUBMITTED (páry studenta nezná)
        resp = self.transition(self.foreign_student, sp, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertIn(resp.status_code, (400, 403))
        self.assertEqual(self.sp_snapshot(sp)["workflow_state"], StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

        # cizí student: upload opravy → HasDocumentAccess 403, bez přechodu
        denied_upload = self._upload(doc, actor=self.foreign_student)
        self.assertEqual(denied_upload.status_code, 403)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

        # cizí student i vlastník NESMÍ generic přejít DR → ENDED (hrana odstraněna)
        resp = self.transition(self.foreign_student, sp, StudentPracticeWorkflowState.ENDED)
        self.assertIn(resp.status_code, (400, 403))
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

        # review-pending: cizí student i cizí profesor odmítnuti
        self.assertEqual(self._upload(doc).status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        snapshot = self.sp_snapshot(sp)
        resp = self.transition(self.foreign_student, sp, StudentPracticeWorkflowState.ENDED)
        self.assertIn(resp.status_code, (400, 403))
        self.assertEqual(self.sp_snapshot(sp), snapshot)
        resp = self.transition(self.foreign_professor, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.sp_snapshot(sp), snapshot)

    # ------------------------------------------------------------------
    # Finding 2 — opravný resubmit hrana je POUZE čin vlastníka-studenta
    # ------------------------------------------------------------------

    def test_ordinary_authorized_upload_does_not_trigger_review_pending(self):
        """Organizace i pedagog smí doklad nahrát (HasDocumentAccess), ale
        stav DOCUMENTS_REJECTED se NESMÍ posunout — resubmit hrana je jen
        vlastníka-studenta; žádná garanti notifikace."""
        sp, doc = self._dr_sp()
        notif_before = Notification.objects.count()

        # organizace (oprávněný uploadér, NE vlastník)
        self.client.force_authenticate(user=self.org_user)
        org_upload = self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile("org-repair.pdf", b"%PDF-1.4 org", content_type="application/pdf")},
        )
        self.assertEqual(org_upload.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(Notification.objects.count(), notif_before)  # žádné garanti „čeká na review"

        # pedagog (oprávněný uploadér, NE vlastník)
        self.client.force_authenticate(user=self.garant)
        prof_upload = self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile("prof-repair.pdf", b"%PDF-1.4 prof", content_type="application/pdf")},
        )
        self.assertEqual(prof_upload.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(Notification.objects.count(), notif_before)

        # kontrast: vlastník-student → hrana ANO (DOCUMENTS_RESUBMITTED)
        self.assertEqual(self._upload(doc).status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertGreater(Notification.objects.count(), notif_before)

    # ------------------------------------------------------------------
    # Finding 5 — review posun JEN se schváleným opraveným dokumentem
    # ------------------------------------------------------------------

    def test_review_transition_requires_approved_feedback_document(self):
        """Brána opravného cyklu (aktuální): do ENDED/AWAITING_DOCUMENTS se
        neprojde bez SCHVÁLENÉHO závěrečného (FEEDBACK) dokumentu; ostatní
        dokumenty jen nesmí být REJECTED.

        Dřívější varianta vyžadovala APPROVED u VŠECH připojených dokumentů;
        nyní PENDING contract/content postup neblokuje, rozhoduje FEEDBACK.
        """
        sp, doc = self._dr_sp()
        self.assertEqual(self._upload(doc).status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        # bez schváleného FEEDBACK dokumentu je postup do ENDED zablokovaný
        premature_final = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(premature_final.status_code, 400)
        self.assertIn("FEEDBACK", premature_final.data.get("detail", ""))
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        premature_mid = self.transition(self.garant, sp, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.assertEqual(premature_mid.status_code, 400)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        # samotné schválení opraveného CONTRACT nestačí — FEEDBACK stále chybí
        self.client.force_authenticate(user=self.garant)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.APPROVED)

        still_blocked = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(still_blocked.status_code, 400)
        self.assertIn("FEEDBACK", still_blocked.data.get("detail", ""))

        # se schváleným FEEDBACK dokumentem precondition projde
        self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        approved_transition = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(approved_transition.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

    def test_review_document_reject_returns_to_documents_rejected(self):
        """Zamítnutí review dokumentu (PATCH review-document) → zpět do
        DOCUMENTS_REJECTED — review řídí postup, ne jen transition."""
        sp, doc = self._dr_sp()
        self.assertEqual(self._upload(doc).status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        self.client.force_authenticate(user=self.garant)
        rejected = self.client.patch(
            f"/api/student-practices/review-document/{doc.pk}",
            {"status": DocumentStatus.REJECTED.value, "review_note": "oprava nevyhovuje"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(sp.rejection_reason, "oprava nevyhovuje")
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.REJECTED)

    # ------------------------------------------------------------------
    # Finding 5 residual (round 3) — precondition musí dokázat schválení
    # PRÁVĚ opravených dokumentů, ne historický APPROVED stav
    # ------------------------------------------------------------------

    def test_repair_advance_requires_review_of_repaired_document_not_historical(self):
        """Historické APPROVED (contract) NEuspokojí precondition za opravený
        FEEDBACK: PENDING oprava blokuje postup (400, nulová mutace/notifikace);
        až review schválí opravený doklad, postup projde."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.APPROVED)  # staré schválení
        rejected_feedback = self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.REJECTED)

        # owner re-upuje zamítnutý FEEDBACK → reset na PENDING + state 13
        self.client.force_authenticate(user=self.owner_student)
        upload = self.client.post(
            f"/api/student-practices/upload-document/{rejected_feedback.pk}",
            {"document": SimpleUploadedFile("repaired-feedback.pdf", b"%PDF-1.4 fb", content_type="application/pdf")},
        )
        self.assertEqual(upload.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        rejected_feedback.refresh_from_db()
        self.assertEqual(rejected_feedback.status, DocumentStatus.PENDING)

        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        # škola chce ENDED — historická APPROVED contract NESMÍ stačit
        premature = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(premature.status_code, 400)
        self.assertIn("FEEDBACK", premature.data.get("detail", ""))
        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

        # review schválí opravený FEEDBACK → precondition splněn
        self.client.force_authenticate(user=self.garant)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{rejected_feedback.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)

        advance = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(advance.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

    def test_repair_advance_requires_approved_feedback_document(self):
        """Více opravených dokumentů: nová brána vyžaduje schválený FEEDBACK,
        ostatní dokumenty jen nesmí být REJECTED.

        PENDING contract/content tedy postup do ENDED neblokuje (dřívější
        varianta vyžadovala APPROVED u všech); bez FEEDBACK dokumentu se ale
        do ENDED neprojde.
        """
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        contract = self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.REJECTED)
        content = self.make_doc(sp, doc_type=DocumentType.CONTENT, status=DocumentStatus.REJECTED)

        self.client.force_authenticate(user=self.owner_student)
        for doc in (contract, content):
            upload = self.client.post(
                f"/api/student-practices/upload-document/{doc.pk}",
                {
                    "document": SimpleUploadedFile(f"repaired-{doc.document_id}.pdf", b"%PDF-1.4 repaired", content_type="application/pdf"),
                },
            )
            self.assertEqual(upload.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        # review schválí jen CONTRACT → CONTENT zůstává PENDING, ale bez
        # schváleného FEEDBACK dokumentu postup stále neprojde.
        self.client.force_authenticate(user=self.garant)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{contract.pk}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        before = self.sp_snapshot(sp)
        premature = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(premature.status_code, 400)
        self.assertIn("FEEDBACK", premature.data.get("detail", ""))
        self.assertEqual(self.sp_snapshot(sp), before)

        # schválený FEEDBACK splní precondition i s PENDING CONTENT → postup projde
        self.make_doc(sp, doc_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        advance = self.transition(self.garant, sp, StudentPracticeWorkflowState.ENDED)
        self.assertEqual(advance.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

    # ------------------------------------------------------------------
    # MINOR (round 3) — operational log bez PII
    # ------------------------------------------------------------------

    def test_non_owner_upload_log_contains_no_actor_email(self):
        """Repair-resubmit skip log smí obsahovat jen necitlivou roli/výsledek
        a opaque SP ID — žádný e-mail aktéra."""
        sp, doc = self._dr_sp()

        with self.assertLogs("student_practices.services", level="INFO") as captured:
            self.client.force_authenticate(user=self.org_user)
            response = self.client.post(
                f"/api/student-practices/upload-document/{doc.pk}",
                {"document": SimpleUploadedFile("org-repair.pdf", b"%PDF-1.4 org", content_type="application/pdf")},
            )

        self.assertEqual(response.status_code, 201)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        log_text = "\n".join(captured.output)
        self.assertIn("Repair-resubmit přeskočen", log_text)
        self.assertNotIn("owner-org@bl03.test", log_text)


# ===================================================================
# Finding 3 — C03-A: nevzaté storno blokuje i přijetí pozvánky
# ===================================================================


class Bl03InvitationC03Tests(BL03FixtureMixin, TestCase):
    APPROVE_URL = "/api/student-practices/employer-invitation/approve/"

    def _accept(self, invitation, actor=None):
        self.client.force_authenticate(user=actor or self.owner_student)
        return self.client.post(
            self.APPROVE_URL,
            {"invitation_id": invitation.invitation_id, "action": "accept"},
            format="json",
        )

    def test_invitation_accept_blocked_by_pending_cancellation(self):
        """F3: storno studentem stejné registrace (student+subject) blokuje
        přijetí pozvánky — nulová mutace; po vzetí na vědomí garantem přijetí projde."""
        # storno na JINÉ praxi téhož předmětu (registrace ≈ subject)
        other_sp = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.CONTRACTED)
        StudentPracticeService.submit_cancellation_request(other_sp, self.owner_student, "BL03 pending cancel")

        invitation = EmployerInvitation.objects.create(
            employer=self.employer,
            user=self.owner_student,
            practice=self.practice_same_subject,
            status=EmployerInvitationStatus.PENDING,
            submission_date=date.today(),
        )
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        # --- blokace: žádná mutace pozvánky/SP/logu/notifikace ---
        denied = self._accept(invitation)
        self.assertEqual(denied.status_code, 400)
        self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(denied.data))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, EmployerInvitationStatus.PENDING)
        self.assertEqual(StudentPractice.objects.filter(practice=self.practice_same_subject, user=self.owner_student).count(), 0)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

        # --- vzetí storna na vědomí garantem odblokuje ---
        self.client.force_authenticate(user=self.garant)
        resolved = self.client.post(
            f"/api/student-practices/{other_sp.student_practice_id}/resolve-cancellation/",
            {},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)

        accepted = self._accept(invitation)
        self.assertEqual(accepted.status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, EmployerInvitationStatus.ACCEPTED)
        sp = StudentPractice.objects.get(practice=self.practice_same_subject, user=self.owner_student)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)
        self.assertTrue(sp.employer_approved)  # vlastní osa z pozvánky (existující chování)


# ===================================================================
# Finding 4 — null-state init bez autorizace
# ===================================================================


class Bl03NullStateInitTests(BL03FixtureMixin, TestCase):
    def test_foreign_student_cannot_initialize_null_state_sp(self):
        """Cizí student na null-state SP → 403, stav zůstává None,
        žádný ActionLog/Notification záznam."""
        sp = self.make_sp(self.owner_student, state=None)
        self.assertIsNone(sp.workflow_state)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.post(
            f"/api/student-practices/{sp.student_practice_id}/transition/",
            {"target_state": StudentPracticeWorkflowState.APPLIED.value},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        sp.refresh_from_db()
        self.assertIsNone(sp.workflow_state)
        self.assertFalse(sp.is_cancelled)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)


# ===================================================================
# 6) C20-A — auto-close jen manuálně (kapacita chráněna; TIME odděleně)
# ===================================================================


class Bl03AutoCloseTests(BL03FixtureMixin, TestCase):
    def test_capacity_auto_close_does_not_fire(self):
        """C20-A: kapacitní auto-close NESMÍ trknout potichu (guard = settings
        AUTO_CLOSE_AT_CAPACITY=False → vypnuto)."""
        practice = self.make_practice(title="BL03 autoclose-cap", available_positions=1, start_days=30)
        self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.CONTRACTED)

        call_command("auto_close_practices", stdout=StringIO())

        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)
        self.assertIsNone(practice.closed_reason)

    def test_time_cutoff_close_still_runs(self):
        """Termínový (TIME) auto-close je SAMOSTATNÝ mechanismus — nedotčen."""
        practice = self.make_practice(title="BL03 autoclose-time", available_positions=10, start_days=-1)

        call_command("auto_close_practices", stdout=StringIO())

        practice.refresh_from_db()
        self.assertEqual(practice.workflow_state, PracticeWorkflowState.CLOSED_FOR_APPLICATIONS)
        self.assertEqual(practice.closed_reason, ApplicationClosureReason.TIME)


# ===================================================================
# 7) T2b — confirm-contract zdrojové stavy + idempotence
# ===================================================================


class Bl03ConfirmT2bTests(BL03FixtureMixin, TestCase):
    def _confirm(self, actor, sp):
        self.client.force_authenticate(user=actor)
        return self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

    def test_confirm_from_ended_denied_no_mutation(self):
        """T2b: jen pre-kontrakční zdrojové stavy (AWAITING_CONTRACT / APPLIED externí)."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.ENDED)

        response = self._confirm(self.owner_student, sp)

        self.assertEqual(response.status_code, 400)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)
        self.assertFalse(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        self.assertIsNone(sp.contract_received_date)
        self.assertIn("předkontrakčních", response.data.get("detail", ""))

    def test_confirm_from_applied_standard_denied(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.APPLIED)

        response = self._confirm(self.owner_student, sp)

        self.assertEqual(response.status_code, 400)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)
        self.assertIsNone(sp.contract_received_date)

    def test_confirm_from_applied_external_allowed(self):
        """T2b: APPLIED je povolen NA EXTERNÍ CESTĚ (standardní APPLIED = 400).
        Externí praxe nemá EmployerProfile → potvrzuje škola (subject scope)."""
        external = self.make_practice(title="BL03 externí", external=True)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.APPLIED)

        response = self._confirm(self.garant, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED)  # jedna osa → pending

    def test_repeat_same_axis_is_idempotent_without_new_notification(self):
        """T2b: opakování stejné osy = 200 no-op, ŽÁDNÁ nová notifikace."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        approve_contract_document(sp)  # A-11: do CONTRACTED jen se schválenou smlouvou

        # první osa (pending, žádná allokační notifikace)
        self.assertEqual(self._confirm(self.org_user, sp).status_code, 200)
        sp.refresh_from_db()
        first_date = sp.contract_received_date
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(), 0)

        # opakování stejné osy → 200 no-op, beze změny data i notifikací
        repeat = self._confirm(self.org_user, sp)
        self.assertEqual(repeat.status_code, 200)
        sp.refresh_from_db()
        self.assertFalse(sp.school_approved)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertEqual(sp.contract_received_date, first_date)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(), 0)

        # druhá osa → CONTRACTED + přesně jedna allokační notifikace
        self.assertEqual(self._confirm(self.garant, sp).status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        advanced_date = sp.contract_received_date
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(), 1)

        # opakování OBOU os po advance → 200 no-op, BEZ duplicitní notifikace
        for actor in (self.org_user, self.garant, self.owner_student):
            again = self._confirm(actor, sp)
            self.assertEqual(again.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.contract_received_date, advanced_date)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=self.org_user).count(), 1)

    def test_confirm_repeat_on_preapproved_pending_reconciles_to_contracted(self):
        """Obě předem schválené osy se při confirm rekoncilují do CONTRACTED."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True, employer_approved=True)
        approve_contract_document(sp)  # A-11: do CONTRACTED jen se schválenou smlouvou
        sp.refresh_from_db()
        self.assertIsNone(sp.contract_received_date)

        alloc_before = Notification.objects.filter(verb="ALLOCATION_ORG").count()

        response = self._confirm(self.garant, sp)
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)
        self.assertIsNotNone(sp.contract_received_date)
        self.assertTrue(sp.school_approved)
        self.assertTrue(sp.employer_approved)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG").count(), alloc_before + 1)


# ===================================================================
# Additive (BL-04 frontend contract): serializer/relations payload
# ===================================================================


class Bl03FrontendContractAdditiveTests(BL03FixtureMixin, TestCase):
    """Additive-only: vystavení cancellation_requested_at/resolved_at
    (card + list serializer), is_external na kartě, workflow_status
    v relations payloadu. Žádná změna chování."""

    def test_sp_card_exposes_cancellation_request_fields_and_is_external(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "BL03 additive")
        sp.refresh_from_db()

        self.client.force_authenticate(user=self.owner_student)
        response = self.client.get(f"/api/student-practices/{sp.student_practice_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["cancellation_requested_at"])
        self.assertIsNone(response.data["cancellation_resolved_at"])
        self.assertFalse(response.data["is_external"])

    def test_sp_card_is_external_true_for_external_practice(self):
        external = self.make_practice(title="BL03 additive ext", external=True)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.APPLIED)

        self.client.force_authenticate(user=self.owner_student)
        response = self.client.get(f"/api/student-practices/{sp.student_practice_id}")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_external"])

    def test_list_serializer_exposes_cancellation_request_fields(self):
        from student_practices.serializers import ListStudentPracticeSerializer

        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.CONTRACTED)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "BL03 additive list")
        sp.refresh_from_db()

        data = ListStudentPracticeSerializer(sp).data

        self.assertIn("cancellation_requested_at", data)
        self.assertIsNotNone(data["cancellation_requested_at"])
        self.assertIn("cancellation_resolved_at", data)
        self.assertIsNone(data["cancellation_resolved_at"])

    def test_user_relations_payload_includes_workflow_status(self):
        from practices.services import PracticeService

        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)

        data = PracticeService.get_user_practices_and_invitations(self.owner_student)
        entry = [e for e in data["student_practices"] if e["student_practice_id"] == sp.student_practice_id][0]

        self.assertEqual(entry["workflow_status"], "AWAITING_CONTRACT")


# ===================================================================
# Finding 1 residual (round 3) — T1 brána uvnitř SLUŽBY (přímá volání)
# ===================================================================


class Bl03ServiceT1GateTests(BL03FixtureMixin, TestCase):
    """Přímé volání ``transition_student_practice_state`` (ne jen HTTP) musí
    selhat transakčně pro KAŽDOU CONTRACTED zdrojovou cestu, chybí-li druhá
    osa — AxesIncompleteError + nulová mutace (žádný save/ActionLog/notifikace)."""

    def test_service_awaiting_contract_requires_both_axes(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        with self.assertRaises(AxesIncompleteError):
            StudentPracticeService.transition_student_practice_state(
                sp=sp,
                target_state=StudentPracticeWorkflowState.CONTRACTED,
                actor=self.garant,
                reason="BL03 service gate",
            )

        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_service_external_content_approved_passes_with_school_axis_and_contract(self):
        """D-1/F-28: externí praxe nemá EmployerProfile — stačí školní osa
        a schválená smlouva (A-11); employer osa se nevyžaduje."""
        external = self.make_practice(title="BL03 svc-ext", external=True)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.CONTENT_APPROVED)
        self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.APPROVED)

        result = StudentPracticeService.transition_student_practice_state(
            sp=sp,
            target_state=StudentPracticeWorkflowState.CONTRACTED,
            actor=self.garant,
            reason="BL03 service gate ext (D-1)",
        )

        self.assertEqual(result.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertTrue(result.school_approved)
        self.assertFalse(result.employer_approved)
        self.assertIsNotNone(result.contract_received_date)
        self.assertEqual(result.approval_status, ApprovalStatus.APPROVED)

    def test_service_standard_content_approved_still_requires_both_axes(self):
        """Standardní praxe bez employer osy dál vyhazuje AxesIncompleteError."""
        sp = self.make_sp(self.owner_student, practice=self.practice, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        with self.assertRaises(AxesIncompleteError):
            StudentPracticeService.transition_student_practice_state(
                sp=sp,
                target_state=StudentPracticeWorkflowState.CONTRACTED,
                actor=self.garant,
                reason="BL03 standard service gate",
            )

        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_service_external_applied_contracted_denied_by_matrix(self):
        """APPLIED-externí je jen confirm-contract cesta; generic služba ji
        matrixem odmítne dřív, než by se dotkla approval os."""
        external = self.make_practice(title="BL03 svc-ext-applied", external=True)
        sp = self.make_sp(self.owner_student, practice=external, state=StudentPracticeWorkflowState.APPLIED)
        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        with self.assertRaises(ValueError):
            StudentPracticeService.transition_student_practice_state(
                sp=sp,
                target_state=StudentPracticeWorkflowState.CONTRACTED,
                actor=self.garant,
                reason="BL03 matrix denial",
            )

        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_document_review_direct_no_advance_without_both_axes(self):
        """Document-review path (přímé volání): dokument schválen školou, ale
        bez employer osy → ŽÁDNÝ postup do CONTRACTED, žádná notifikace
        (vlastní osa zapsána — schválení review je školní akt)."""
        practice = self.make_practice(title="BL03 doc-gate", available_positions=10)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.make_doc(sp, doc_type=DocumentType.CONTRACT, status=DocumentStatus.APPROVED)
        log_before = ActionLog.objects.count()

        StudentPracticeService._apply_document_approval_state(sp, self.garant)

        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)  # žádný postup
        self.assertFalse(sp.employer_approved)  # cizí osa NE nastavena
        self.assertTrue(sp.school_approved)  # vlastní (školní) osa zapsána
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)
        self.assertFalse(Notification.objects.filter(verb__in=("APPLICATION_CONTRACTED", "ALLOCATION_ORG")).exists())
        self.assertEqual(ActionLog.objects.count(), log_before)

    def test_record_own_axis_unknown_role_writes_no_axis(self):
        """Helper není autorizace: neznámá role nezapíše žádnou osu."""
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        plain_user = get_user_model().objects.create_user(email="plain-actor@bl03.test", password="bl03-only-password", is_active=True)

        both = record_own_approval_axis(sp, plain_user)
        self.assertFalse(both)
        self.assertFalse(sp.school_approved)
        self.assertFalse(sp.employer_approved)

        both = record_own_approval_axis(sp, self.garant)
        self.assertTrue(sp.school_approved)
        self.assertFalse(sp.employer_approved)  # škola nikdy nezapíše employer osu
        self.assertFalse(both)


# ===================================================================
# Soubežnost (BE-005): skutečný row-lock závod = PostgreSQL; BLOCKED pod SQLite
# ===================================================================


class CapacityConcurrencyPostgresTests(TransactionTestCase):
    """Skutečný souběžný check-then-write závod vyžaduje PostgreSQL row locks.

    Pod SQLite audit wrapperem je test označen BLOCKED (skip), NEPASS —
    důkaz disposable DB i PG běhu vlastní BL-07.
    """

    def test_parallel_allocations_never_exceed_capacity(self):
        if connection.vendor != "postgresql":
            self.skipTest(
                "BLOCKED: souběžný row-lock závod vyžaduje PostgreSQL — "
                "BL-07 vlastní důkaz disposable DB; pod SQLite audit wrapperem se to netvrdí jako PASS."
            )

        from student_practices.services import StudentPracticeService as Svc

        department = Department.objects.create(department_name="PG KI", department_code="PGKI")
        subject = Subject.objects.create(subject_name="PG praxe", subject_code="PG/BOP", department=department)
        professor = ProfessorUser.objects.create_user(
            email="pg-prof@bl03.test",
            password="bl03-only-password",
            first_name="PG",
            last_name="Prof",
            is_active=True,
            department=department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        employer = EmployerProfile.objects.create(company_name="PG Org", approval_status=ApprovalStatus.APPROVED)
        practice = Practice.objects.create(
            title="PG race praxe",
            employer=employer,
            subject=subject,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=1,
        )
        students = [
            StudentUser.objects.create(email=f"pg-student-{i}@bl03.test", first_name="PG", last_name=str(i), is_active=True) for i in (1, 2)
        ]
        sps = [
            StudentPractice.objects.create(
                user=student,
                practice=practice,
                workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
                approval_status=ApprovalStatus.PENDING,
                progress_status=ProgressStatus.NOT_STARTED,
                start_date=date.today(),
                end_date=date.today(),
            )
            for student in students
        ]
        # T1 service gate: employer osa musí držet, aby závod měřil KAPACITU (ne osy)
        StudentPractice.objects.filter(pk__in=[sp.pk for sp in sps]).update(employer_approved=True)
        for sp in sps:
            approve_contract_document(sp)  # A-11

        barrier = threading.Barrier(2, timeout=15)
        succeeded: list[int] = []
        failures: list[Exception] = []

        def allocate(sp_id: int):
            try:
                barrier.wait()
                sp = StudentPractice.objects.get(pk=sp_id)
                Svc.transition_student_practice_state(
                    sp=sp,
                    target_state=StudentPracticeWorkflowState.CONTRACTED,
                    actor=professor,
                    reason="PG race",
                )
                succeeded.append(sp_id)
            except ValueError:
                pass  # CAPACITY_FULL očekáváno u právě jednoho
            except Exception as exc:  # noqa: BLE001 — zaznamenat pro diagnózu
                failures.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=allocate, args=(sp.pk,)) for sp in sps]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(failures, [], f"neočekávané chyby v závodu: {failures}")
        contracted = StudentPractice.objects.filter(practice=practice, workflow_state=StudentPracticeWorkflowState.CONTRACTED).count()
        self.assertEqual(contracted, 1, "souběžná alokace překročila kapacitu 1")
        self.assertEqual(len(succeeded), 1)


class SimulatedRaceSqliteSafeTests(BL03FixtureMixin, TestCase):
    """SQLite-safe simulace: serializované pořadí writerů (v PG je vynuceno
    select_for_update) — druhý writer musí narazit na plnou kapacitu."""

    def test_second_writer_blocked_after_first_commits(self):
        practice = self.make_practice(title="BL03 race-sim", available_positions=1)
        sp_a = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        sp_b = self.make_sp(self.other_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.make_doc(sp_a, status=DocumentStatus.APPROVED)
        self.make_doc(sp_b, status=DocumentStatus.APPROVED)
        # T1 brána: employer osa musí držet, aby simulace měřila KAPACITU
        StudentPractice.objects.filter(pk__in=[sp_a.pk, sp_b.pk]).update(employer_approved=True)
        sp_a.refresh_from_db()
        sp_b.refresh_from_db()

        # Writer A: check+write atomicky → CONTRACTED
        StudentPracticeService._apply_document_approval_state(sp_a, self.garant)
        sp_a.refresh_from_db()
        self.assertEqual(sp_a.workflow_state, StudentPracticeWorkflowState.CONTRACTED)

        # Writer B: jeho check probíhá AŽ po zápisu A (serializace) → blokace
        StudentPracticeService._apply_document_approval_state(sp_b, self.garant)
        sp_b.refresh_from_db()
        self.assertEqual(sp_b.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.assertEqual(
            StudentPractice.objects.filter(practice=practice, workflow_state=StudentPracticeWorkflowState.CONTRACTED).count(),
            1,
        )
