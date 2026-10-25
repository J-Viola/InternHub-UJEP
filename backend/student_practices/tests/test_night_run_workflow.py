from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase

from practices.models import ExternalEmployerInfo, Practice, PracticeWorkflowState
from practices.services import PracticeService
from student_practices.models import DocumentStatus, DocumentType, StudentPracticeWorkflowState
from student_practices.services import StudentPracticeService
from student_practices.tests.test_bl03_workflow import BL03FixtureMixin
from users.models import ActionLog, ApprovalStatus


class NightRunWorkflowTests(BL03FixtureMixin, TestCase):
    def _upload(self, doc, actor=None):
        self.client.force_authenticate(user=actor or self.owner_student)
        return self.client.post(
            f"/api/student-practices/upload-document/{doc.pk}",
            {"document": SimpleUploadedFile("replacement.pdf", b"%PDF-1.7 test", content_type="application/pdf")},
        )

    def _confirm(self, actor, sp):
        self.client.force_authenticate(user=actor)
        return self.client.post(f"/api/student-practices/{sp.pk}/confirm-contract/")

    def test_resubmit_only_rejected_uploads_and_owner_resets_document(self):
        sp, rejected = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED), None
        rejected = self.make_doc(sp, status=DocumentStatus.REJECTED)
        pending = self.make_doc(sp, doc_type=DocumentType.CONTENT, status=DocumentStatus.PENDING)
        self.assertEqual(self._upload(pending).status_code, 201)
        sp.refresh_from_db()
        rejected.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(rejected.status, DocumentStatus.REJECTED)

        rejected.review_note = "Opravte"
        rejected.save(update_fields=["review_note"])
        self.assertEqual(self._upload(rejected).status_code, 201)
        sp.refresh_from_db()
        rejected.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertEqual(rejected.status, DocumentStatus.PENDING)
        self.assertEqual(rejected.review_note, "")

    def test_upload_of_non_rejected_document_resets_it_to_pending_without_transition(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        approved = self.make_doc(sp, status=DocumentStatus.APPROVED)
        approved.review_note = "Původní poznámka"
        approved.save(update_fields=["review_note"])

        self.assertEqual(self._upload(approved).status_code, 201)
        approved.refresh_from_db()
        sp.refresh_from_db()
        self.assertEqual(approved.status, DocumentStatus.PENDING)
        self.assertEqual(approved.review_note, "")
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

    def test_non_owner_upload_does_not_clear_rejection_and_second_rejected_doc_resets(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        first = self.make_doc(sp, status=DocumentStatus.REJECTED)
        second = self.make_doc(sp, doc_type=DocumentType.CONTENT, status=DocumentStatus.REJECTED)
        denied_actor = self.org_user
        self._upload(first, denied_actor)
        sp.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(first.status, DocumentStatus.REJECTED)

        self.assertEqual(self._upload(first).status_code, 201)
        self.assertEqual(self._upload(second).status_code, 201)
        sp.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertEqual(second.status, DocumentStatus.PENDING)

    def test_pending_cancellation_freezes_transition_confirm_and_review_but_can_resolve(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        doc = self.make_doc(sp, status=DocumentStatus.PENDING)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "Důvod")
        with self.assertRaisesRegex(ValueError, "čeká na rozhodnutí"):
            StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.CONTRACTED, self.garant)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertEqual(self._confirm(self.garant, sp).status_code, 400)
        with self.assertRaisesRegex(ValueError, "čeká na rozhodnutí"):
            StudentPracticeService.process_document_review(self.garant, doc.pk, DocumentStatus.APPROVED)
        sp.refresh_from_db()
        doc.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertEqual(doc.status, DocumentStatus.PENDING)
        StudentPracticeService.resolve_cancellation(sp, self.garant, decision="reject")
        sp.refresh_from_db()
        self.assertIsNotNone(sp.cancellation_resolved_at)

    def test_rejected_cancellation_can_be_requested_again_then_approved(self):
        sp = self.make_sp(self.owner_student)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "První důvod")
        StudentPracticeService.resolve_cancellation(sp, self.garant, decision="reject")
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "Druhý důvod")
        sp.refresh_from_db()
        self.assertIsNone(sp.cancellation_resolved_at)
        StudentPracticeService.resolve_cancellation(sp, self.garant, decision="approve")
        sp.refresh_from_db()
        self.assertTrue(sp.is_cancelled)

    def test_external_pending_application_is_creator_only(self):
        external_info = ExternalEmployerInfo.objects.create(name="Externí", created_by=self.owner_student)
        practice = self.make_practice(external=True, workflow_state=PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        practice.external_employer = external_info
        practice.save(update_fields=["external_employer"])
        with self.assertRaisesRegex(ValueError, "PRACTICE_NOT_OPEN_FOR_APPLICATIONS"):
            PracticeService.apply_student_practice(self.other_student, practice.pk)
        self.assertFalse(practice.student_practices.filter(user=self.other_student).exists())
        result = PracticeService.apply_student_practice(self.owner_student, practice.pk)
        self.assertTrue(practice.student_practices.filter(user=self.owner_student).exists())
        self.assertIsNotNone(result)

    def test_confirm_reconciles_preapproved_axes_and_capacity_blocks(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        type(sp).objects.filter(pk=sp.pk).update(employer_approved=True, school_approved=True)
        sp.refresh_from_db()
        response = self._confirm(self.garant, sp)
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)

        full = self.make_sp(self.other_student, state=StudentPracticeWorkflowState.AWAITING_CONTRACT)
        type(full).objects.filter(pk=full.pk).update(employer_approved=True, school_approved=True)
        Practice.objects.filter(pk=self.practice.pk).update(available_positions=1)
        self.make_sp(self.foreign_student, state=StudentPracticeWorkflowState.CONTRACTED)
        response = self._confirm(self.garant, full)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        full.refresh_from_db()
        self.assertEqual(full.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)

        # A row already CONTRACTED remains idempotent.
        contracted = self.make_sp(self.foreign_student, practice=self.practice_other_subject, state=StudentPracticeWorkflowState.CONTRACTED)
        type(contracted).objects.filter(pk=contracted.pk).update(school_approved=True)
        self.assertEqual(self._confirm(self.garant, contracted).status_code, 200)

    def test_cancel_email_is_registered_after_commit_and_discarded_on_rollback(self):
        sp = self.make_sp(self.owner_student)
        with patch(
            "student_practices.services.EmailService.notify_student_cancellation",
            side_effect=lambda *a: mail.send_mail("cancel", "body", "from@example.test", ["to@example.test"]),
        ):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                StudentPracticeService.cancel_student_practice(sp, self.garant, "Zrušení")
                self.assertEqual(len(mail.outbox), 0)
            self.assertTrue(callbacks)

            with self.captureOnCommitCallbacks(execute=True):
                StudentPracticeService.cancel_student_practice(self.make_sp(self.other_student), self.garant, "Zrušení")
            self.assertGreater(len(mail.outbox), 0)
            count_after_commit = len(mail.outbox)

            try:
                with transaction.atomic():
                    StudentPracticeService.cancel_student_practice(self.make_sp(self.foreign_student), self.garant, "Rollback")
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            self.assertEqual(len(mail.outbox), count_after_commit)

    def test_audit_descriptions_do_not_include_email_addresses(self):
        sp = self.make_sp(self.owner_student)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "Důvod")
        StudentPracticeService.resolve_cancellation(sp, self.garant, decision="reject")
        logs = ActionLog.objects.filter(object_id=sp.pk)
        self.assertTrue(logs.exists())
        self.assertTrue(all("@" not in log.action_description for log in logs))

        reviewed = self.make_doc(sp, status=DocumentStatus.PENDING)
        StudentPracticeService.process_document_review(self.garant, reviewed.pk, DocumentStatus.APPROVED)
        self.assertNotIn("@", ActionLog.objects.filter(object_id=reviewed.pk).latest("action_date").action_description)

    def test_terminal_rejection_persists_reason(self):
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/student-practices/{sp.pk}/transition/",
            {"target_state": StudentPracticeWorkflowState.REJECTED.value, "reason": "Konečný důvod"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        sp.refresh_from_db()
        self.assertEqual(sp.rejection_reason, "Konečný důvod")
