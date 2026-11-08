"""Regresní testy pro rozsah staff přehledů a admin fronty nabídek."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
    StudentUser,
    User,
    UserSubject,
    UserSubjectType,
)


class StaffRunningScopeTests(TestCase):
    """VK/HEAD nesmí přes /staff/running/ vidět praxe jiné katedry."""

    def setUp(self):
        self.client = APIClient()
        self.dept_a = Department.objects.create(department_name="Katedra A", department_code="KA")
        self.dept_b = Department.objects.create(department_name="Katedra B", department_code="KB")
        self.subject_a = Subject.objects.create(subject_code="KA/PRAX", subject_name="Praxe A", department=self.dept_a)
        self.subject_b = Subject.objects.create(subject_code="KB/PRAX", subject_name="Praxe B", department=self.dept_b)

        self.org_user = OrganizationUser.objects.create(
            email="org@staff-scope.test", password="pass", first_name="Org", last_name="User", is_active=True
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Scope Corp",
            address="Praha",
            approval_status=ApprovalStatus.APPROVED,
        )

        vk_role, _ = StagRole.objects.get_or_create(role=StagRoleEnum.VK, defaults={"role_name": "Vedoucí katedry"})
        self.vk = ProfessorUser.objects.create(
            email="vk@staff-scope.test",
            first_name="Vedoucí",
            last_name="Katedry",
            is_active=True,
            stag_role=vk_role,
            department=self.dept_a,
            department_role=DepartmentRole.HEAD,
        )

        self.student_a = StudentUser.objects.create(email="student-a@staff-scope.test", os_cislo="SA1", is_active=True)
        self.student_b = StudentUser.objects.create(email="student-b@staff-scope.test", os_cislo="SB1", is_active=True)
        UserSubject.objects.create(user=self.student_a, subject=self.subject_a, role=UserSubjectType.Student)
        UserSubject.objects.create(user=self.student_b, subject=self.subject_b, role=UserSubjectType.Student)

        self.practice_a = self._practice("Praxe A", self.subject_a)
        self.practice_b = self._practice("Praxe B", self.subject_b)
        self._student_practice(self.student_a, self.practice_a)
        self._student_practice(self.student_b, self.practice_b)

    def _practice(self, title, subject):
        today = date.today()
        return Practice.objects.create(
            title=title,
            description="Testovací praxe",
            employer=self.employer,
            subject=subject,
            contact_user=self.org_user,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=100),
            available_positions=3,
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

    def _student_practice(self, student, practice):
        today = date.today()
        return StudentPractice.objects.create(
            user=student,
            practice=practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
            start_date=today,
            end_date=today + timedelta(days=30),
        )

    def test_vk_sees_only_own_department(self):
        self.client.force_authenticate(user=self.vk)
        response = self.client.get(reverse("practices:staff-practices-running"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        ids = {item["practice_id"] for item in data}
        self.assertIn(self.practice_a.practice_id, ids)
        self.assertNotIn(self.practice_b.practice_id, ids)

    def test_superuser_sees_all_departments(self):
        admin = User.objects.create_user(email="admin@staff-scope.test", password="pass", is_active=True, is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("practices:staff-practices-running"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        ids = {item["practice_id"] for item in data}
        self.assertIn(self.practice_a.practice_id, ids)
        self.assertIn(self.practice_b.practice_id, ids)


class AdminActiveOffersTests(TestCase):
    """Nabídka otevřená přes /transition/ musí být v active_offers, ne ve frontě."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@active-offers.test", password="pass", is_active=True, is_staff=True, is_superuser=True
        )
        self.dept = Department.objects.create(department_name="Katedra", department_code="K")
        self.subject = Subject.objects.create(subject_code="K/PRAX", subject_name="Praxe", department=self.dept)
        self.org_user = OrganizationUser.objects.create(
            email="org@active-offers.test", password="pass", first_name="Org", last_name="User", is_active=True
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Offers Corp",
            address="Praha",
            approval_status=ApprovalStatus.APPROVED,
        )

    def _practice(self, title, approval_status, workflow_state):
        today = date.today()
        return Practice.objects.create(
            title=title,
            description="Testovací praxe",
            employer=self.employer,
            subject=self.subject,
            contact_user=self.org_user,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=100),
            available_positions=3,
            is_active=True,
            approval_status=approval_status,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=workflow_state,
        )

    def test_transitioned_open_offer_is_active_and_not_pending(self):
        open_offer = self._practice("Otevřená přes transition", ApprovalStatus.PENDING, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)
        pending = self._practice("Čeká na schválení", ApprovalStatus.PENDING, PracticeWorkflowState.PENDING_CONTENT_APPROVAL)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("practices:admin-practices"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        active_ids = {item["practice_id"] for item in response.data["active_offers"]}
        pending_ids = {item["practice_id"] for item in response.data["to_approve_practices"]}
        self.assertIn(open_offer.practice_id, active_ids)
        self.assertNotIn(open_offer.practice_id, pending_ids)
        self.assertIn(pending.practice_id, pending_ids)

    def test_active_offers_expose_application_counts(self):
        offer = self._practice("Aktivní nabídka", ApprovalStatus.APPROVED, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)
        student = StudentUser.objects.create(email="student@active-offers.test", os_cislo="AO1", is_active=True)
        StudentPractice.objects.create(
            user=student,
            practice=offer,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("practices:admin-practices"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(entry for entry in response.data["active_offers"] if entry["practice_id"] == offer.practice_id)
        self.assertEqual(item["approved_applications"], 1)
        self.assertEqual(item["pending_applications"], 0)
