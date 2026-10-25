"""A-11 — přechod do CONTRACTED vyžaduje schválený smluvní dokument.

BP: „Do stavu CONTRACTED se přihláška dostane, jen jsou-li schváleny obě strany,
je volná kapacita a smluvní dokument je schválen.“ Admin override neexistuje.
Testy pokrývají KAŽDOU zdrojovou hranu do CONTRACTED v ``SP_TRANSITIONS``
i ``MANUAL_SP_TRANSITIONS`` + confirm-contract.
"""

from django.test import TestCase
from notifications.models import Notification
from test_support.contracts import approve_contract_document

from student_practices.models import (
    DocumentStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.services import (
    MANUAL_SP_TRANSITIONS,
    SP_TRANSITIONS,
    ContractDocumentNotApprovedError,
    StudentPracticeService,
)
from student_practices.tests.test_bl03_workflow import BL03FixtureMixin
from users.models import ActionLog

CONTRACTED = StudentPracticeWorkflowState.CONTRACTED


def _edges(matrix):
    return sorted((src for src, targets in matrix.items() if CONTRACTED in targets), key=lambda s: s.value)


class ContractGateEveryEdgeTests(BL03FixtureMixin, TestCase):
    def _both_axes(self, sp):
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True, employer_approved=True)
        sp.refresh_from_db()

    def _assert_blocked(self, sp):
        before = self.sp_snapshot(sp)
        log_before = ActionLog.objects.count()
        notif_before = Notification.objects.count()

        response = self.transition(self.garant, sp, CONTRACTED)

        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data.get("error_code"), "CONTRACT_NOT_APPROVED")
        self.assertEqual(self.sp_snapshot(sp), before)
        self.assertEqual(ActionLog.objects.count(), log_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_every_standard_edge_blocked_without_approved_contract(self):
        edges = _edges(SP_TRANSITIONS)
        self.assertTrue(edges)
        for source in edges:
            with self.subTest(source=source.name):
                practice = self.make_practice(title=f"A11 std {source.name}", available_positions=5)
                sp = self.make_sp(self.owner_student, practice=practice, state=source)
                self._both_axes(sp)
                self._assert_blocked(sp)

    def test_every_manual_edge_blocked_without_approved_contract(self):
        edges = _edges(MANUAL_SP_TRANSITIONS)
        self.assertTrue(edges)
        for source in edges:
            with self.subTest(source=source.name):
                practice = self.make_practice(title=f"A11 man {source.name}", available_positions=5, external=True)
                sp = self.make_sp(self.owner_student, practice=practice, state=source)
                self._both_axes(sp)
                self._assert_blocked(sp)

    def test_pending_or_rejected_contract_does_not_count(self):
        practice = self.make_practice(title="A11 pending", available_positions=5)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self._both_axes(sp)
        self.make_doc(sp, status=DocumentStatus.PENDING)
        self._assert_blocked(sp)

    def test_service_raises_domain_error_before_any_write(self):
        practice = self.make_practice(title="A11 service", available_positions=5)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self._both_axes(sp)
        with self.assertRaises(ContractDocumentNotApprovedError):
            StudentPracticeService.transition_student_practice_state(sp, CONTRACTED, self.garant)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)

    def test_axes_incomplete_has_priority_over_missing_contract(self):
        practice = self.make_practice(title="A11 axes", available_positions=5)
        sp = self.make_sp(self.owner_student, practice=practice, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        response = self.transition(self.garant, sp, CONTRACTED)
        self.assertEqual(response.data.get("error_code"), "AXES_INCOMPLETE")

    def test_positive_both_axes_capacity_and_approved_contract(self):
        for source in _edges(SP_TRANSITIONS):
            with self.subTest(source=source.name):
                practice = self.make_practice(title=f"A11 ok {source.name}", available_positions=5)
                sp = self.make_sp(self.owner_student, practice=practice, state=source)
                self._both_axes(sp)
                approve_contract_document(sp)
                response = self.transition(self.garant, sp, CONTRACTED)
                self.assertEqual(response.status_code, 200, response.data)
                sp.refresh_from_db()
                self.assertEqual(sp.workflow_state, CONTRACTED)


class ConfirmContractGateTests(BL03FixtureMixin, TestCase):
    def _confirm(self, actor, sp):
        self.client.force_authenticate(user=actor)
        return self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")

    def test_confirm_with_both_axes_but_unapproved_contract_stays_put(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True)

        response = self._confirm(self.org_user, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertTrue(sp.employer_approved)
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG").count(), 0)

    def test_confirm_with_approved_contract_reaches_contracted(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True)
        approve_contract_document(sp)

        response = self._confirm(self.org_user, sp)

        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, CONTRACTED)
