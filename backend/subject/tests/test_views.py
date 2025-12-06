from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Department, DepartmentRole, ProfessorUser, StagRole, Subject
from users.models import StagRoleEnum


class SubjectViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(department_name="Computer Science", department_code="KI")
        self.stag_role_vy = StagRole.objects.create(role=StagRoleEnum.VY, role_name="Teacher")

        self.professor = ProfessorUser.objects.create(
            email="prof@test.com",
            first_name="Prof",
            last_name="One",
            department=self.department,
            department_role=DepartmentRole.HEAD,
            stag_role=self.stag_role_vy,
            is_active=True,
        )

        self.subject = Subject.objects.create(
            subject_name="Intro to CS",
            subject_code="KI/101",
            department=self.department,
        )

        self.other_department = Department.objects.create(department_name="Math", department_code="KMA")
        self.other_subject = Subject.objects.create(
            subject_name="Calculus",
            subject_code="KMA/101",
            department=self.other_department,
        )

        self.url = "/api/subjects/department-subjects/"

    def test_department_subjects_access_denied_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_professor_sees_only_own_department_subjects(self):
        self.client.force_authenticate(user=self.professor)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["subject_code"], "KI/101")
