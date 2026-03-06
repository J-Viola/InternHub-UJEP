from datetime import date, datetime, timedelta

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
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class PracticeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Setup Organization
        self.org_user = OrganizationUser.objects.create(
            email="org@test.com",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Test Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer_profile
        self.org_user.save()

        # Setup Another Organization (Attacker)
        self.other_org_user = OrganizationUser.objects.create(
            email="other@test.com",
            password="pass",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        self.other_employer_profile = EmployerProfile.objects.create(
            employer_id=self.other_org_user.id,
            company_name="Other Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.other_org_user.employer_profile = self.other_employer_profile
        self.other_org_user.save()

        # Setup Student
        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Student",
            last_name="One",
            is_active=True,
        )

        # Setup Dept & Subject
        self.dept = Department.objects.create(department_name="IT", department_code="KI")
        self.subject = Subject.objects.create(subject_name="Java", department=self.dept)

        # Setup Professor
        from users.models import StagRole

        self.prof_role = StagRole.objects.create(role="VY", role_name="Vyučující")
        self.professor = ProfessorUser.objects.create(
            email="prof@test.com",
            first_name="Prof",
            last_name="User",
            is_active=True,
            stag_role=self.prof_role,
            department=self.dept,
        )

        # Setup Practice
        self.practice = Practice.objects.create(
            employer=self.employer_profile,
            subject=self.subject,
            title="Java Dev",
            description="Code Java",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            is_active=True,
            coefficient=1.0,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

    def test_list_practices_authenticated(self):
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["title"], "Java Dev")

    def test_organization_practices_annotations(self):
        self.client.force_authenticate(user=self.org_user)

        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        url = "/api/practices/organization_practices/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data[0]

        self.assertEqual(data["approved_applications"], 1)
        self.assertEqual(data["pending_applications"], 0)

    def test_apply_student_practice_action(self):
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/apply_student_practice/"

        data = {"practice": self.practice.practice_id}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StudentPractice.objects.filter(user=self.student, practice=self.practice).exists())

    def test_apply_student_practice_duplicate_fail(self):
        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        self.client.force_authenticate(user=self.student)
        url = "/api/practices/apply_student_practice/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_create_practice_as_organization(self):
        self.client.force_authenticate(user=self.org_user)
        url = "/api/practices/"

        data = {
            "subject_id": self.subject.subject_id,
            "title": "New Practice",
            "description": "Desc",
            "start_date": datetime.today().strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Practice.objects.count(), 2)
        new_practice = Practice.objects.get(title="New Practice")
        self.assertEqual(new_practice.employer, self.employer_profile)
        # Check defaults
        self.assertEqual(new_practice.progress_status, ProgressStatus.NOT_STARTED)

    def test_change_pending_status(self):
        self.practice.approval_status = ApprovalStatus.PENDING
        self.practice.save()

        url = f"/api/practices/{self.practice.practice_id}/change-pending/"
        data = {"approval_status": ApprovalStatus.APPROVED.value}

        # Authenticate as someone with permission
        self.client.force_authenticate(user=self.professor)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.approval_status, ApprovalStatus.APPROVED)

    def test_create_practice_invalid_dates(self):
        """Test that end_date cannot be before start_date"""
        self.client.force_authenticate(user=self.org_user)
        url = "/api/practices/"

        today = date.today()
        yesterday = today - timedelta(days=1)

        data = {
            "subject_id": self.subject.subject_id,
            "title": "Invalid Dates Practice",
            "start_date": today.strftime("%d.%m.%Y"),
            "end_date": yesterday.strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Depending on serializer, it might be under 'non_field_errors' or field name
        self.assertTrue(response.data)

    def test_student_cannot_delete_practice(self):
        """Test that a student cannot delete a practice"""
        self.client.force_authenticate(user=self.student)
        url = f"/api/practices/{self.practice.practice_id}/"

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Practice.objects.filter(pk=self.practice.practice_id).exists())

    def test_organization_cannot_edit_other_practice(self):
        """Test that an organization cannot edit practice of another organization"""
        self.client.force_authenticate(user=self.other_org_user)
        url = f"/api/practices/{self.practice.practice_id}/"

        data = {"title": "Hacked Title"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.practice.refresh_from_db()
        self.assertNotEqual(self.practice.title, "Hacked Title")
