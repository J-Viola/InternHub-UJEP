import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import ApprovalStatus, EmployerProfile, OrganizationRole, OrganizationUser, StudentUser


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        # Setup Student
        self.student = StudentUser.objects.create_user(
            email="student@test.com", password="password123", first_name="Jan", last_name="Student", is_active=True
        )

        # Setup Organization User
        self.org_user = OrganizationUser.objects.create_user(
            email="org@test.com",
            password="password123",
            first_name="Boss",
            last_name="CEO",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id, company_name="Test Co", approval_status=ApprovalStatus.APPROVED
        )
        self.org_user.employer_profile = self.profile
        self.org_user.save()

        self.profile_url = reverse("users:current_user_profile")

    def test_student_profile_update_skills_json_string(self):
        """Test that skills can be sent as a JSON string (typical for multipart/form-data)"""
        self.client.force_authenticate(user=self.student)
        skills_data = ["Python", "Django", "React"]
        data = {"skills": json.dumps(skills_data), "first_name": "Honza"}
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.student.refresh_from_db()
        self.assertEqual(self.student.skills, skills_data)
        self.assertEqual(self.student.first_name, "Honza")

    def test_student_profile_update_skills_list(self):
        """Test that skills can be sent as a direct list (typical for JSON requests)"""
        self.client.force_authenticate(user=self.student)
        skills_data = ["C++", "Qt"]
        data = {"skills": skills_data}
        response = self.client.patch(self.profile_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.student.refresh_from_db()
        self.assertEqual(self.student.skills, skills_data)

    def test_student_profile_update_cv_file(self):
        """Test uploading a CV file"""
        self.client.force_authenticate(user=self.student)
        cv_file = SimpleUploadedFile("resume.pdf", b"pdf content", content_type="application/pdf")
        data = {"cv_file": cv_file}
        # Use multipart for file upload
        response = self.client.patch(self.profile_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.student.refresh_from_db()
        self.assertIn("resume", self.student.cv_file.name)
        self.assertTrue(self.student.cv_file.name.endswith(".pdf"))

    def test_validate_email_uniqueness(self):
        """Test that updating to an already existing email fails"""
        self.client.force_authenticate(user=self.student)
        data = {"email": "org@test.com"}
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_validate_email_allow_same_email(self):
        """Test that keeping the same email during update doesn't trigger uniqueness error"""
        self.client.force_authenticate(user=self.student)
        data = {"email": "student@test.com", "first_name": "Updated"}
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Updated")

    def test_organization_profile_update(self):
        """Test that organization user can update basic info"""
        self.client.force_authenticate(user=self.org_user)
        data = {"first_name": "NewBoss", "phone": "987654321"}
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.org_user.refresh_from_db()
        self.assertEqual(self.org_user.first_name, "NewBoss")
        self.assertEqual(self.org_user.phone, "987654321")

    def test_student_profile_update_invalid_skills_json(self):
        """Test that invalid JSON in skills returns 400 error"""
        self.client.force_authenticate(user=self.student)
        data = {"skills": "invalid-json-{[}"}
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skills", response.data)
