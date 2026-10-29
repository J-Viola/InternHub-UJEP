from datetime import date

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from test_support.contracts import approve_contract_document

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from student_practices.serializers import StudentPracticeWithDetailsSerializer
from student_practices.services import StudentPracticeService
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class ContractAndCancellationRegressionTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="rf@test.cz", first_name="Test", last_name="Student", is_active=True)
        self.org = OrganizationUser.objects.create(email="rf-org@test.cz", is_active=True, organization_role=0)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org.id, company_name="RF Company", approval_status=ApprovalStatus.APPROVED
        )
        self.practice = Practice.objects.create(
            title="RF practice",
            employer=self.employer,
            subject=self.subject,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=5,
        )
        self.actor = ProfessorUser.objects.create_user(
            email="rf-prof@test.cz",
            password="pw",
            first_name="Test",
            last_name="Professor",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
            is_superuser=True,
        )

    def create_sp(self, state):
        return StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
            school_approved=True,
            employer_approved=True,
        )

    def test_transition_to_contracted_sets_date_once(self):
        sp = self.create_sp(StudentPracticeWorkflowState.AWAITING_CONTRACT)
        approve_contract_document(sp)  # A-11
        StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.CONTRACTED, self.actor)
        sp.refresh_from_db()
        first_date = sp.contract_received_date
        self.assertIsNotNone(first_date)
        sp.workflow_state = StudentPracticeWorkflowState.AWAITING_CONTRACT
        sp.save(update_fields=["workflow_state"])
        StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.CONTRACTED, self.actor)
        sp.refresh_from_db()
        self.assertEqual(sp.contract_received_date, first_date)

    def test_document_approval_entry_sets_contract_date(self):
        sp = self.create_sp(StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        doc = UploadedDocument.objects.create(document_type=0, status=DocumentStatus.APPROVED)
        sp.contract_document = doc
        sp.save(update_fields=["contract_document"])
        StudentPracticeService._apply_document_approval_state(sp, self.actor)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(sp.contract_received_date)

    def test_confirm_contract_entry_sets_date_once(self):
        sp = self.create_sp(StudentPracticeWorkflowState.AWAITING_CONTRACT)
        sp.school_approved = True
        sp.employer_approved = False
        sp.save(update_fields=["school_approved", "employer_approved"])
        self.org.employer_profile = self.employer
        self.org.save()
        approve_contract_document(sp)  # A-11
        client = APIClient()
        client.force_authenticate(user=self.org)
        response = client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        sp.refresh_from_db()
        original_date = sp.contract_received_date
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(original_date)

    def test_cancelled_from_state_is_captured_and_immutable(self):
        sp = self.create_sp(StudentPracticeWorkflowState.STARTED)
        sp = StudentPracticeService.cancel_student_practice(sp, self.actor, "test cancellation")
        sp.refresh_from_db()
        self.assertEqual(sp.cancelled_from_state, StudentPracticeWorkflowState.STARTED)
        StudentPracticeService.resolve_cancellation(sp, self.actor)
        sp.refresh_from_db()
        self.assertEqual(sp.cancelled_from_state, StudentPracticeWorkflowState.STARTED)

    def test_patch_cannot_write_cancelled_from_state(self):
        sp = self.create_sp(StudentPracticeWorkflowState.STARTED)
        serializer = StudentPracticeWithDetailsSerializer(
            sp,
            data={"cancelled_from_state": StudentPracticeWorkflowState.APPLIED.value},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        sp.refresh_from_db()
        self.assertIsNone(sp.cancelled_from_state)

    def test_student_cancellation_records_original_state_and_acknowledge_keeps_it(self):
        """A-12: okamžité storno uloží původní stav; vzetí na vědomí ho nemění."""
        sp = self.create_sp(StudentPracticeWorkflowState.STARTED)
        sp = StudentPracticeService.submit_cancellation_request(sp, self.student, "please cancel")
        self.assertTrue(sp.is_cancelled)
        self.assertEqual(sp.cancelled_from_state, StudentPracticeWorkflowState.STARTED)
        sp = StudentPracticeService.resolve_cancellation(sp, self.actor)
        sp.refresh_from_db()
        self.assertEqual(sp.cancelled_from_state, StudentPracticeWorkflowState.STARTED)

    def test_organization_cannot_approve_foreign_practice_or_write_axis(self):
        other_org = OrganizationUser.objects.create(email="other-org@test.cz", is_active=True, organization_role=0)
        EmployerProfile.objects.create(employer_id=other_org.id, company_name="Other", approval_status=ApprovalStatus.APPROVED)
        sp = self.create_sp(StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        sp.employer_approved = False
        sp.save(update_fields=["employer_approved"])

        with self.assertRaises(PermissionDenied):
            StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.AWAITING_CONTRACT, other_org)

        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        self.assertFalse(sp.employer_approved)

    def test_owning_organization_transition_writes_employer_axis(self):
        self.org.employer_profile = self.employer
        self.org.save(update_fields=["employer_profile"])
        sp = self.create_sp(StudentPracticeWorkflowState.PRELIMINARY_APPROVED)
        sp.employer_approved = False
        sp.save(update_fields=["employer_approved"])

        StudentPracticeService.transition_student_practice_state(sp, StudentPracticeWorkflowState.AWAITING_CONTRACT, self.org)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertTrue(sp.employer_approved)  # schválení organizací zapisuje vlastní osu (rozhodnutí autora, review 26. 10.)
