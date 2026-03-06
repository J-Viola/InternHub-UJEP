from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,  # Import OrganizationRole
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class PracticeAndStudentApplicationWorkflowTests(TestCase):  # Renamed for clarity
    def setUp(self):
        self.client = APIClient()

        # Create Department and Subject for practices
        self.department = Department.objects.create(department_name="Test Dept", department_code="TD")
        self.subject = Subject.objects.create(
            subject_name="Test Subject",
            subject_code="TS101",
            department=self.department,
        )

        # Create Users
        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Jan",
            last_name="Novak",
            is_active=True,
        )
        self.professor = ProfessorUser.objects.create(
            email="prof@test.com",
            first_name="Karel",
            last_name="Profesor",
            is_active=True,
        )
        self.other_organization_user = OrganizationUser.objects.create(
            email="other_org@test.com",
            is_active=True,
            organization_role=OrganizationRole.INSERTER,  # Added role
        )
        self.other_employer_profile = EmployerProfile.objects.create(
            employer_id=self.other_organization_user.id,
            company_name="Other Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.other_organization_user.employer_profile = self.other_employer_profile
        self.other_organization_user.save()

        # Create Employer & Profile (for the main practice)
        self.employer_user = OrganizationUser.objects.create(
            email="employer@test.com",
            is_active=True,
            organization_role=OrganizationRole.OWNER,  # Set as OWNER
        )
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.employer_user.id,
            company_name="Test Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.employer_user.employer_profile = self.employer_profile
        self.employer_user.save()

        # Create Active Practice
        self.practice = Practice.objects.create(
            title="Python Developer",
            description="Backend dev",
            employer=self.employer_profile,
            subject=self.subject,
            contact_user=self.employer_user,
            available_positions=5,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            coefficient=1.0,
        )

        self.practice_list_url = "/api/practices/"
        self.apply_url = "/api/practices/apply_student_practice/"

    # --- Existing Student Application Tests ---
    def test_student_can_apply_for_active_practice(self):
        self.client.force_authenticate(user=self.student)
        data = {"practice": self.practice.practice_id}

        response = self.client.post(self.apply_url, data, format="json")  # Added format="json"

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify DB
        application = StudentPractice.objects.filter(user=self.student, practice=self.practice).first()
        self.assertIsNotNone(application)
        self.assertEqual(application.approval_status, ApprovalStatus.PENDING)

    def test_student_cannot_apply_twice_for_same_practice(self):
        self.client.force_authenticate(user=self.student)
        data = {"practice": self.practice.practice_id}

        # First application
        self.client.post(self.apply_url, data, format="json")  # Added format="json"

        # Second application
        response = self.client.post(self.apply_url, data, format="json")  # Added format="json"

        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_apply_for_non_existent_practice(self):
        self.client.force_authenticate(user=self.student)
        data = {"practice": 99999}

        response = self.client.post(self.apply_url, data, format="json")  # Added format="json"

        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )

    def test_anonymous_user_cannot_apply(self):
        data = {"practice": self.practice.practice_id}
        response = self.client.post(self.apply_url, data, format="json")  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- New Practice CRUD Tests ---

    def test_organization_user_can_create_practice(self):
        self.client.force_authenticate(user=self.employer_user)
        new_practice_data = {
            "title": "New Practice Title",
            "description": "New Description",
            "responsibilities": "New responsibilities",
            "available_positions": 3,
            "start_date": "01.07.2050",  # Changed year to 2050
            "end_date": "31.12.2050",  # Changed year to 2050
            "coefficient": 1.0,
            "subject_id": self.subject.subject_id,
            "employer_id": self.employer_profile.employer_id,
            "contact_user": self.employer_user.user_id,
        }

        response = self.client.post(self.practice_list_url, new_practice_data, format="json")  # Added format="json"

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_practice = Practice.objects.get(title="New Practice Title")
        self.assertEqual(created_practice.employer, self.employer_profile)
        self.assertEqual(created_practice.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(created_practice.progress_status, ProgressStatus.NOT_STARTED)

    def test_student_cannot_create_practice(self):
        self.client.force_authenticate(user=self.student)
        new_practice_data = {
            "title": "Student Created Practice",
            "description": "Desc",
            "responsibilities": "Resp",
            "available_positions": 1,
            "start_date": "01.07.2050",  # Changed year to 2050
            "end_date": "31.12.2050",  # Changed year to 2050
            "coefficient": 1.0,
            "subject_id": self.subject.subject_id,
            "employer_id": self.employer_profile.employer_id,
            "contact_user": self.employer_user.user_id,
        }
        response = self.client.post(self.practice_list_url, new_practice_data, format="json")  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_professor_cannot_create_practice(self):
        self.client.force_authenticate(user=self.professor)
        new_practice_data = {
            "title": "Professor Created Practice",
            "description": "Desc",
            "responsibilities": "Resp",
            "available_positions": 1,
            "start_date": "01.07.2050",  # Changed year to 2050
            "end_date": "31.12.2050",  # Changed year to 2050
            "coefficient": 1.0,
            "subject_id": self.subject.subject_id,
            "employer_id": self.employer_profile.employer_id,
            "contact_user": self.employer_user.user_id,
        }
        response = self.client.post(self.practice_list_url, new_practice_data, format="json")  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organization_user_can_update_own_practice(self):
        self.client.force_authenticate(user=self.employer_user)
        update_data = {"title": "Updated Title"}
        response = self.client.patch(
            f"{self.practice_list_url}{self.practice.practice_id}/",
            update_data,
            format="json",
        )  # Added format="json"

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.title, "Updated Title")

    def test_other_organization_user_cannot_update_practice(self):
        self.client.force_authenticate(user=self.other_organization_user)
        update_data = {"title": "Malicious Update"}
        response = self.client.patch(
            f"{self.practice_list_url}{self.practice.practice_id}/",
            update_data,
            format="json",
        )  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_update_practice(self):
        self.client.force_authenticate(user=self.student)
        update_data = {"title": "Student Update"}
        response = self.client.patch(
            f"{self.practice_list_url}{self.practice.practice_id}/",
            update_data,
            format="json",
        )  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_professor_cannot_update_practice(self):
        self.client.force_authenticate(user=self.professor)
        update_data = {"title": "Professor Update"}
        response = self.client.patch(
            f"{self.practice_list_url}{self.practice.practice_id}/",
            update_data,
            format="json",
        )  # Added format="json"
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
