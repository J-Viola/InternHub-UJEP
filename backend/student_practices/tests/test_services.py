from datetime import date

from django.test import TestCase

from practices.models import Practice, ProgressStatus
from student_practices.models import (
    EmployerInvitation,
    EmployerInvitationStatus,
    StudentPractice,
)
from student_practices.services import StudentPracticeService
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    StudentUser,
)


class StudentPracticeServiceTests(TestCase):
    def setUp(self):
        self.user = StudentUser.objects.create(
            email="student@test.com", first_name="S", last_name="U"
        )
        self.other_user = StudentUser.objects.create(
            email="thief@test.com", first_name="T", last_name="H"
        )
        self.employer_user = OrganizationUser.objects.create(
            email="emp@test.com", first_name="E", last_name="O"
        )
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.employer_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )

        self.practice = Practice.objects.create(
            title="Test Practice",
            coefficient=1.0,
            employer=self.employer_profile,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        self.invitation = EmployerInvitation.objects.create(
            user=self.user,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
            employer=self.employer_profile,
        )

    def test_process_invitation_approval_accept(self):
        # Ensure StudentPractice does not exist initially for this specific test
        StudentPractice.objects.filter(user=self.user, practice=self.practice).delete()

        result = StudentPracticeService.process_invitation_approval(
            self.user, self.invitation.invitation_id, "accept"
        )

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, EmployerInvitationStatus.ACCEPTED)

        sp = StudentPractice.objects.get(user=self.user, practice=self.practice)
        # Now it's PENDING until school approves
        self.assertEqual(sp.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(sp.progress_status, ProgressStatus.NOT_STARTED)
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)
        self.assertIn("student_practice_id", result)

    def test_process_invitation_approval_reject(self):
        StudentPracticeService.process_invitation_approval(
            self.user, self.invitation.invitation_id, "reject"
        )

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, EmployerInvitationStatus.REJECTED)
        self.assertFalse(
            StudentPractice.objects.filter(
                user=self.user, practice=self.practice
            ).exists()
        )

    def test_process_invitation_approval_invalid_action(self):
        with self.assertRaises(ValueError):
            StudentPracticeService.process_invitation_approval(
                self.user, self.invitation.invitation_id, "invalid"
            )

    def test_process_invitation_not_found(self):
        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(self.user, 999, "accept")
        self.assertIn("INVITATION_NOT_FOUND", str(cm.exception))

    def test_process_invitation_already_processed(self):
        self.invitation.status = EmployerInvitationStatus.ACCEPTED
        self.invitation.save()

        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(
                self.user, self.invitation.invitation_id, "accept"
            )
        self.assertIn("INVITATION_PROCESSED", str(cm.exception))

    def test_process_invitation_wrong_user(self):
        other_user = StudentUser.objects.create(
            email="other@student.cz", is_active=True
        )
        with self.assertRaises(ValueError) as cm:
            StudentPracticeService.process_invitation_approval(
                other_user, self.invitation.invitation_id, "accept"
            )
        self.assertIn("INVITATION_NOT_FOUND", str(cm.exception))
