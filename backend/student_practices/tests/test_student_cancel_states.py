"""
Storno studentem podle analýzy (§4.2, D-05, BDD UC-05 AC-02): okamžité, z libovolného aktivního stavu
před finálním uzavřením. Konečné stavy REJECTED a COMPLETED stornovat nelze.
"""

from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)

W = StudentPracticeWorkflowState


class StudentCancelStateRuleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        department = Department.objects.create(department_name="IT", department_code="IT")
        subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=department)
        self._students = 0
        org_user = OrganizationUser.objects.create(email="o@test.com", is_active=True, organization_role=0)
        employer = EmployerProfile.objects.create(employer_id=org_user.id, company_name="Test Co", approval_status=ApprovalStatus.APPROVED)
        org_user.employer_profile = employer
        org_user.save()
        self.head = ProfessorUser.objects.create_user(
            email="h@test.com",
            password="password123",
            first_name="Head",
            last_name="Prof",
            is_active=True,
            department=department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.practice = Practice.objects.create(
            title="Dev Job",
            employer=employer,
            subject=subject,
            contact_user=org_user,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=5,
        )

    def _sp(self, state):
        # unikátní aktivní přihláška na studenta → každý případ má vlastního studenta
        self._students += 1
        student = StudentUser.objects.create(email=f"s{self._students}@test.com", first_name="Jan", last_name="Student", is_active=True)
        return StudentPractice.objects.create(
            user=student,
            practice=self.practice,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
        )

    def _cancel(self, user, sp, reason="Zdravotní důvody"):
        self.client.force_authenticate(user=user)
        return self.client.post(f"/api/student-practices/{sp.student_practice_id}/cancel/", {"reason": reason})

    def test_student_can_cancel_from_any_active_state(self):
        active = [st for st in W if st not in (W.REJECTED, W.COMPLETED)]
        self.assertIn(W.STARTED, active)
        self.assertIn(W.AWAITING_CONTRACT, active)
        for state in active:
            with self.subTest(state=state.name):
                sp = self._sp(state)
                response = self._cancel(sp.user, sp)
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
                sp.refresh_from_db()
                self.assertTrue(sp.is_cancelled)
                self.assertEqual(sp.cancelled_from_state, state)

    def test_student_cannot_cancel_final_states(self):
        for state in (W.REJECTED, W.COMPLETED):
            with self.subTest(state=state.name):
                sp = self._sp(state)
                response = self._cancel(sp.user, sp)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                sp.refresh_from_db()
                self.assertFalse(sp.is_cancelled)
                self.assertEqual(sp.workflow_state, state)

    def test_garant_can_cancel_started_practice(self):
        sp = self._sp(W.STARTED)
        response = self._cancel(self.head, sp, reason="Ukončení spolupráce")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        sp.refresh_from_db()
        self.assertTrue(sp.is_cancelled)
        self.assertEqual(sp.cancelled_from_state, W.STARTED)
