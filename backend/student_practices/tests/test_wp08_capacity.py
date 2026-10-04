"""kapacita při alokaci → CONTRACTED; notifikace org."""

from datetime import date

from django.test import TestCase
from notifications.models import Notification
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from student_practices.services import StudentPracticeService
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class CapacityAllocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)

        self.student = StudentUser.objects.create(email="student@cap.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(
            email="org@cap.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Cap Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.professor = ProfessorUser.objects.create_user(
            email="prof@cap.test",
            password="password123",
            first_name="Karel",
            last_name="Prof",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )

        # Kapacita 1 místo
        self.practice = Practice.objects.create(
            title="Kapacitní praxe",
            employer=self.employer,
            subject=self.subject,
            contact_user=self.org_user,
            start_date=date.today(),
            end_date=date.today(),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=1,
        )

    def _sp(self, workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT):
        return StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=workflow_state,
        )

    def test_transition_to_contracted_rejected_when_full(self):
        """Plná kapacita → přechod do CONTRACTED odmítnut (ValueError CAPACITY_FULL)."""
        # První student už je CONTRACTED
        self._sp().save()
        StudentPractice.objects.filter(user=self.student).update(workflow_state=StudentPracticeWorkflowState.CONTRACTED)

        other_student = StudentUser.objects.create(email="student2@cap.test", first_name="Petr", last_name="Druhý", is_active=True)
        sp2 = StudentPractice.objects.create(
            user=other_student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.transition_student_practice_state(
                sp2,
                StudentPracticeWorkflowState.CONTRACTED,
                self.professor,
                reason="test",
            )
        self.assertEqual(str(cm.exception), "CAPACITY_FULL")

    def test_confirm_contract_rejected_when_full(self):
        """ConfirmContractView → plná kapacita → 400 CAPACITY_FULL (česká hláška)."""
        # Jeden student už CONTRACTED
        sp = self._sp()
        sp.workflow_state = StudentPracticeWorkflowState.CONTRACTED
        sp.save()

        other_student = StudentUser.objects.create(email="student2@cap.test", first_name="Petr", last_name="Druhý", is_active=True)
        sp2 = StudentPractice.objects.create(
            user=other_student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )
        self.client.force_authenticate(user=self.org_user)
        response = self.client.post(f"/api/student-practices/{sp2.student_practice_id}/confirm-contract/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "CAPACITY_FULL")
        self.assertEqual(response.data.get("detail"), "Kapacita partnera je plně obsazena")

    def test_contracted_notifies_org(self):
        """Po úspěšném CONTRACTED vzniká notifikace organizaci (verb ALLOCATION_ORG)."""
        sp = self._sp()  # AWAITING_CONTRACT
        StudentPracticeService.transition_student_practice_state(
            sp,
            StudentPracticeWorkflowState.CONTRACTED,
            self.professor,
            reason="test",
        )
        notif = Notification.objects.filter(recipient=self.org_user, verb="ALLOCATION_ORG").first()
        self.assertIsNotNone(notif, "ALLOCATION_ORG notifikace měla vzniknout")

    def test_contracted_allowed_when_capacity_available(self):
        """Volná kapacita → CONTRACTED projde."""
        sp = self._sp()
        sp = StudentPracticeService.transition_student_practice_state(
            sp,
            StudentPracticeWorkflowState.CONTRACTED,
            self.professor,
            reason="test",
        )
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
