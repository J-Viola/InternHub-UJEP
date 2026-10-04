"""expozice dat — rejection_reason, uploaded_at, late_submission."""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import DocumentHelper, StudentPractice, StudentPracticeWorkflowState
from student_practices.serializers import ListStudentPracticeSerializer, StudentPracticeCardSerializer
from subject.models import Subject
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser, StudentUser


class SerializerExposureTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="student@ser.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="org@ser.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Ser Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.practice = Practice.objects.create(
            title="Ser praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            rejection_reason="Nesplňuje požadavky pro tuto praxi",
        )
        DocumentHelper.assign_default_documents(self.sp)
        self.sp.refresh_from_db()

    def test_list_serializer_includes_rejection_reason(self):
        data = ListStudentPracticeSerializer(self.sp).data
        self.assertIn("rejection_reason", data)
        self.assertEqual(data["rejection_reason"], "Nesplňuje požadavky pro tuto praxi")

    def test_card_serializer_includes_rejection_reason(self):
        data = StudentPracticeCardSerializer(self.sp).data
        self.assertIn("rejection_reason", data)
        self.assertEqual(data["rejection_reason"], "Nesplňuje požadavky pro tuto praxi")

    def test_student_practice_status_serializer_includes_rejection_reason(self):
        """FE čte `entity.student_practice_status.rejection_reason` — kritický payload."""
        data = StudentPracticeCardSerializer(self.sp).data
        status = data["student_practice_status"]
        self.assertIn("rejection_reason", status)
        self.assertEqual(status["rejection_reason"], "Nesplňuje požadavky pro tuto praxi")
        # workflow_status je string enumu (FE matchuje na tyto stringy)
        self.assertEqual(status["workflow_status"], "APPLIED")
        self.assertIn("workflow_status_label", status)

    def test_student_practice_status_workflow_status_string_values(self):
        """workflow_status vrací stringy enumu, na které FE matchuje (REJECTED, DOCUMENTS_REJECTED…)."""
        from student_practices.models import StudentPracticeWorkflowState

        self.sp.workflow_state = StudentPracticeWorkflowState.DOCUMENTS_REJECTED
        self.sp.save()
        data = StudentPracticeCardSerializer(self.sp).data
        status = data["student_practice_status"]
        self.assertEqual(status["workflow_status"], "DOCUMENTS_REJECTED")

    def test_card_document_payload_has_uploaded_at_and_late_submission(self):
        contract = self.sp.contract_document
        contract.late_submission = True
        contract.uploaded_at = timezone.now()
        contract.save()

        data = StudentPracticeCardSerializer(self.sp).data
        docs = data["student_practice_documents"]
        self.assertTrue(docs)
        contract_payload = next(d for d in docs if d["type"] == "contract")
        self.assertIn("uploaded_at", contract_payload)
        self.assertIsNotNone(contract_payload["uploaded_at"])
        self.assertTrue(contract_payload["late_submission"])
