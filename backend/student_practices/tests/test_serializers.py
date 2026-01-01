from datetime import timedelta

from django.test import TestCase

from student_practices.models import (
    StudentPractice,
)
from student_practices.serializers import (
    CreateInvitationSerializer,
    EmployerInvitationApprovalSerializer,
    StudentPracticeSerializer,
)
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser, StudentUser

# ===========================================================================
# EmployerInvitationApprovalSerializer
# ===========================================================================


class EmployerInvitationApprovalSerializerTests(TestCase):
    def test_accept_action_is_valid(self):
        s = EmployerInvitationApprovalSerializer(
            data={"invitation_id": 1, "action": "accept"}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_reject_action_is_valid(self):
        s = EmployerInvitationApprovalSerializer(
            data={"invitation_id": 2, "action": "reject"}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_action_rejected(self):
        s = EmployerInvitationApprovalSerializer(
            data={"invitation_id": 1, "action": "approve"}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("action", s.errors)

    def test_missing_invitation_id_rejected(self):
        s = EmployerInvitationApprovalSerializer(data={"action": "accept"})
        self.assertFalse(s.is_valid())
        self.assertIn("invitation_id", s.errors)

    def test_missing_action_rejected(self):
        s = EmployerInvitationApprovalSerializer(data={"invitation_id": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("action", s.errors)

    def test_non_integer_invitation_id_rejected(self):
        s = EmployerInvitationApprovalSerializer(
            data={"invitation_id": "abc", "action": "accept"}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("invitation_id", s.errors)


# ===========================================================================
# CreateInvitationSerializer
# ===========================================================================


class CreateInvitationSerializerTests(TestCase):
    def test_valid_data_passes(self):
        s = CreateInvitationSerializer(
            data={"practice_id": 1, "student_ids": [10, 20, 30]}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_empty_student_ids_list_is_valid(self):
        # serializer accepts an empty list — business logic handles the empty case elsewhere
        s = CreateInvitationSerializer(data={"practice_id": 1, "student_ids": []})
        self.assertTrue(s.is_valid(), s.errors)

    def test_missing_practice_id_rejected(self):
        s = CreateInvitationSerializer(data={"student_ids": [1, 2]})
        self.assertFalse(s.is_valid())
        self.assertIn("practice_id", s.errors)

    def test_missing_student_ids_rejected(self):
        s = CreateInvitationSerializer(data={"practice_id": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("student_ids", s.errors)

    def test_non_integer_practice_id_rejected(self):
        s = CreateInvitationSerializer(data={"practice_id": "abc", "student_ids": [1]})
        self.assertFalse(s.is_valid())
        self.assertIn("practice_id", s.errors)

    def test_non_integer_in_student_ids_rejected(self):
        s = CreateInvitationSerializer(
            data={"practice_id": 1, "student_ids": [1, "bad", 3]}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("student_ids", s.errors)


# ===========================================================================
# StudentPracticeSerializer — read fields present in serialised output
# ===========================================================================


class StudentPracticeSerializerTests(TestCase):
    def setUp(self):
        self.profile = EmployerProfile.objects.create(
            company_name="Test Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org = OrganizationUser.objects.create(
            email="org@sp-test.com",
            first_name="Org",
            last_name="User",
            is_active=True,
            employer_profile=self.profile,
        )
        self.student = StudentUser.objects.create(
            email="student@sp-test.com",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )

    def test_required_fields_present_in_output(self):
        from datetime import date

        from student_practices.models import ProgressStatus

        sp = StudentPractice.objects.create(
            user=self.student,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            application_date=date.today(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
        )
        data = StudentPracticeSerializer(sp).data
        for field in ("student_practice_id", "approval_status", "progress_status"):
            self.assertIn(field, data)

    def test_user_info_contains_full_name(self):
        from datetime import date

        from student_practices.models import ProgressStatus

        sp = StudentPractice.objects.create(
            user=self.student,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            application_date=date.today(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
        )
        data = StudentPracticeSerializer(sp).data
        self.assertIsNotNone(data.get("user_info"))
        self.assertIn("full_name", data["user_info"])
