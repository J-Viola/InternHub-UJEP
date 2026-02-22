from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from subject.models import Subject
from users.models import (
    DepartmentRole,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
    StudentUser,
    UserSubject,
    UserSubjectType,
)


class DepartmentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create Department
        self.department = Department.objects.create(department_name="Computer Science", department_code="KI")
        self.other_department = Department.objects.create(department_name="Mathematics", department_code="KMA")

        # Create StagRole
        self.stag_role_vy = StagRole.objects.create(role=StagRoleEnum.VY, role_name="Teacher")
        self.stag_role_st = StagRole.objects.create(role=StagRoleEnum.ST, role_name="Student")

        # Create Professor
        self.professor = ProfessorUser.objects.create(
            email="prof@test.com",
            first_name="Prof",
            last_name="One",
            department=self.department,
            department_role=DepartmentRole.HEAD,
            stag_role=self.stag_role_vy,
            is_active=True,
        )

        # Create Student in Department (via Subject)
        self.subject = Subject.objects.create(
            subject_name="Intro to CS",
            subject_code="KI/101",
            department=self.department,
        )
        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Student",
            last_name="One",
            stag_role=self.stag_role_st,
            is_active=True,
        )
        UserSubject.objects.create(user=self.student, subject=self.subject, role=UserSubjectType.Student)

        # Create Student in OTHER Department
        self.other_subject = Subject.objects.create(
            subject_name="Calculus",
            subject_code="KMA/101",
            department=self.other_department,
        )
        self.other_student = StudentUser.objects.create(
            email="other@test.com",
            first_name="Other",
            last_name="Student",
            stag_role=self.stag_role_st,
            is_active=True,
        )
        UserSubject.objects.create(
            user=self.other_student,
            subject=self.other_subject,
            role=UserSubjectType.Student,
        )

        self.url_students = "/api/departments/department-students/"
        self.url_professors = "/api/departments/department-professor/"

    def test_department_student_list_access_denied_unauthenticated(self):
        response = self.client.get(self.url_students)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_professor_sees_own_department_students(self):
        self.client.force_authenticate(user=self.professor)
        response = self.client.get(self.url_students)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 1
        )  # Should include pagination if StandardResultsSetPagination is used, but let's check structure
        # If paginated, data is in response.data['results']
        results = response.data["results"] if "results" in response.data else response.data

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["user_id"], self.student.id)

    def test_professor_sees_own_department_professors(self):
        self.client.force_authenticate(user=self.professor)
        response = self.client.get(self.url_professors)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data

        # Should see themselves (and potentially others if added)
        self.assertTrue(any(p["user_id"] == self.professor.id for p in results))
