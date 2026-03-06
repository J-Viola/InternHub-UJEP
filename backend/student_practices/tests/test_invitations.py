from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from practices.models import Practice, ProgressStatus
from student_practices.models import (
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
)
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    StudentUser,
)


class EmployerInvitationTests(APITestCase):
    def setUp(self):
        # 1. Setup Users
        self.student = StudentUser.objects.create_user(
            email="student@test.com",
            password="password123",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )
        self.other_student = StudentUser.objects.create_user(
            email="other@test.com",
            password="password123",
            first_name="Petr",
            last_name="Other",
            is_active=True,
        )

        self.org_user = OrganizationUser.objects.create_user(
            email="org@test.com",
            password="password123",
            first_name="Boss",
            last_name="CEO",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.profile
        self.org_user.save()

        # 2. Setup Practice
        self.practice = Practice.objects.create(
            employer=self.profile,
            title="Invitation Practice",
            description="Desc",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            coefficient=1.0,
        )

        self.create_url = reverse("student_practices:employer-invitation-create")
        self.approve_url = reverse("student_practices:employer-invitation-approve")

    def test_create_invitations_success(self):
        self.client.force_authenticate(user=self.org_user)
        data = {
            "practice_id": self.practice.practice_id,
            "student_ids": [self.student.id, self.other_student.id],
        }
        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 2)
        self.assertEqual(EmployerInvitation.objects.count(), 2)

    def test_create_invitation_unauthorized_practice(self):
        # Create another org
        other_org_user = OrganizationUser.objects.create_user(email="otherorg@test.com", password="password123", is_active=True)
        # Give them their own profile so they are a valid Org Owner for the permission check
        other_profile = EmployerProfile.objects.create(
            employer_id=other_org_user.id,
            company_name="Other Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        other_org_user.employer_profile = other_profile
        other_org_user.save()

        self.client.force_authenticate(user=other_org_user)

        data = {
            "practice_id": self.practice.practice_id,
            "student_ids": [self.student.id],
        }
        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_accept_invitation(self):
        # Create invitation first
        invitation = EmployerInvitation.objects.create(
            employer=self.profile,
            user=self.student,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            submission_date=date.today(),
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self.approve_url,
            {"invitation_id": invitation.invitation_id, "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, EmployerInvitationStatus.ACCEPTED)

        # Verify StudentPractice created
        self.assertTrue(StudentPractice.objects.filter(user=self.student, practice=self.practice).exists())
        sp = StudentPractice.objects.get(user=self.student, practice=self.practice)
        # Now it is NOT_STARTED and PENDING until school approves
        self.assertEqual(sp.progress_status, ProgressStatus.NOT_STARTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)
        # Verify documents assigned
        self.assertIsNotNone(sp.contract_document)

    def test_student_reject_invitation(self):
        invitation = EmployerInvitation.objects.create(
            employer=self.profile,
            user=self.student,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            submission_date=date.today(),
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self.approve_url,
            {"invitation_id": invitation.invitation_id, "action": "reject"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, EmployerInvitationStatus.REJECTED)
        self.assertFalse(StudentPractice.objects.filter(user=self.student, practice=self.practice).exists())

    def test_manage_invitation_unauthorized_user(self):
        invitation = EmployerInvitation.objects.create(
            employer=self.profile,
            user=self.student,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            submission_date=date.today(),
        )

        # Authenticate as OTHER student
        self.client.force_authenticate(user=self.other_student)
        response = self.client.post(
            self.approve_url,
            {"invitation_id": invitation.invitation_id, "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
