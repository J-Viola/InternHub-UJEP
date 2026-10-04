"""
Tests for department.services —: get_department_professors returns TEACHER and HEAD.
"""

from django.test import TestCase

from department.models import Department
from department.services import get_department_professors
from users.models import DepartmentRole, ProfessorUser, StagRole, StagRoleEnum


class DepartmentServicesTest(TestCase):
    """Verify get_department_professors includes both TEACHER and HEAD roles."""

    def setUp(self):
        self.department = Department.objects.create(department_name="Computer Science", department_code="KI")
        self.stag_role_vy = StagRole.objects.create(role=StagRoleEnum.VY, role_name="Teacher")

        # Teacher (TEACHER=0)
        self.teacher = ProfessorUser.objects.create(
            email="teacher@test.com",
            first_name="Teacher",
            last_name="One",
            department=self.department,
            department_role=DepartmentRole.TEACHER,
            stag_role=self.stag_role_vy,
            is_active=True,
        )
        # Head (HEAD=1)
        self.head = ProfessorUser.objects.create(
            email="head@test.com",
            first_name="Head",
            last_name="One",
            department=self.department,
            department_role=DepartmentRole.HEAD,
            stag_role=self.stag_role_vy,
            is_active=True,
        )

    def test_get_department_professors_returns_teacher(self):
        """TEACHER (department_role=0) must be included in results."""
        professors = get_department_professors(self.teacher)
        self.assertIn(self.teacher, professors, "TEACHER must appear in department professors")

    def test_get_department_professors_returns_head(self):
        """HEAD (department_role=1) must be included in results."""
        professors = get_department_professors(self.head)
        self.assertIn(self.head, professors, "HEAD must appear in department professors")

    def test_get_department_professors_returns_both(self):
        """Both TEACHER and HEAD must be returned for the same department."""
        professors = get_department_professors(self.head)
        self.assertIn(self.teacher, professors)
        self.assertIn(self.head, professors)
        self.assertEqual(professors.count(), 2)
