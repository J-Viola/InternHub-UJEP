from datetime import date, datetime, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
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
            organization_role=OrganizationRole.OWNER,
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
            organization_role=OrganizationRole.OWNER,
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

        self.prof_role = StagRole.objects.create(role="vy", role_name="Vyučující")
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
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

    def test_list_practices_authenticated(self):
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/student/"
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

        url = "/api/practices/employer/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check results in paginated response
        results = response.data["results"] if "results" in response.data else response.data
        data = results[0]

        self.assertEqual(data["approved_count"], 1)
        self.assertEqual(data["pending_count"], 0)

    def test_apply_student_practice_action(self):
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/student/apply/"

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
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        self.client.force_authenticate(user=self.student)
        url = "/api/practices/student/apply/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ALREADY_APPLIED", str(response.data.get("detail", "")))

    def test_create_practice_as_organization(self):
        self.client.force_authenticate(user=self.org_user)
        url = "/api/practices/employer/"

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
        self.practice.workflow_state = PracticeWorkflowState.PENDING_CONTENT_APPROVAL
        self.practice.save()

        url = f"/api/practices/staff/{self.practice.practice_id}/approve/"
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
        url = "/api/practices/employer/"

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
        # Use student URL or employer URL? Deletion is defined in EmployerViewSet.
        # Students shouldn't even have access to that route.
        url = f"/api/practices/employer/{self.practice.practice_id}/"

        response = self.client.delete(url)
        # Since student is not an OrganizationUser, EmployerPracticeViewSet.get_permissions should fail
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Practice.objects.filter(pk=self.practice.practice_id).exists())

    def test_organization_cannot_edit_other_practice(self):
        """Test that an organization cannot edit practice of another organization"""
        self.client.force_authenticate(user=self.other_org_user)
        url = f"/api/practices/employer/{self.practice.practice_id}/"

        data = {"title": "Hacked Title"}
        response = self.client.patch(url, data)

        # Permission class IsOrganizationOwner will catch this and return 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.practice.refresh_from_db()
        self.assertNotEqual(self.practice.title, "Hacked Title")

    # ===========================================================================
    # C3.1 + C3.2 — workflow_state is set on apply and practice creation
    # ===========================================================================

    def test_apply_student_practice_creates_with_workflow_state_applied(self):
        """C3.1: Ensure StudentPractice gets workflow_state=APPLIED on creation."""
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/student/apply/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sp = StudentPractice.objects.filter(user=self.student, practice=self.practice).first()
        self.assertIsNotNone(sp)
        # C3.1: workflow_state must be APPLIED, not None
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.APPLIED, msg="workflow_state should be APPLIED after apply")

    # ===========================================================================
    # C3.5 — Only students can apply
    # ===========================================================================

    def test_apply_student_practice_only_for_students(self):
        """C3.5: Non-student users cannot apply for practices."""
        # Organization user tries to apply
        self.client.force_authenticate(user=self.org_user)
        url = "/api/practices/student/apply/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Professor tries to apply
        self.client.force_authenticate(user=self.professor)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ===========================================================================
    # C3.3 — Capacity guard
    # ===========================================================================

    def test_apply_student_practice_respects_capacity(self):
        """C3.3: Cannot apply when available_positions is full."""
        # Set capacity to 1 and fill it
        self.practice.available_positions = 1
        self.practice.save()

        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        # Create a second student
        student2 = StudentUser.objects.create(
            email="student2@test.com",
            first_name="Student",
            last_name="Two",
            is_active=True,
        )
        self.client.force_authenticate(user=student2)
        url = "/api/practices/student/apply/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("CAPACITY_FULL", str(response.data.get("detail", "")))

    # ===========================================================================
    # 3.7 — Blokace storna praxe
    # ===========================================================================

    def test_apply_student_practice_cancelled_practice(self):
        """3.7: Aplikace na stornovanou praxi musí být zamítnuta."""
        self.practice.is_cancelled = True
        self.practice.save(update_fields=["is_cancelled"])
        self.client.force_authenticate(user=self.student)
        url = "/api/practices/student/apply/"
        data = {"practice": self.practice.practice_id}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PRACTICE_IS_CANCELLED", str(response.data.get("detail", "")))

    # ===========================================================================
    # C3.7 — External practice preserves ico, address, contact_phone
    # ===========================================================================

    def test_external_practice_preserves_ico_address_phone(self):
        """C3.7: External practice creation should persist ico, address, contact_phone."""
        from practices.models import ExternalEmployerInfo

        self.client.force_authenticate(user=self.student)
        url = "/api/practices/external/"

        today = date.today()
        data = {
            "employer_name": "Externí Firma s.r.o.",
            "contact_person": "Jan Novák",
            "contact_email": "jan@firma.cz",
            "ico": "12345678",
            "address": "Náměstí 1, Praha",
            "contact_phone": "+420123456789",
            "subject_id": self.subject.subject_id,
            "title": "Externí praxe",
            "description": "Popis externí praxe",
            "start_date": today.strftime("%d.%m.%Y"),
            "coefficient": 1.0,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=f"External practice response: {response.data}")
        practice_id = response.data.get("practice_id")
        practice = Practice.objects.get(practice_id=practice_id)
        self.assertIsNotNone(practice.external_employer)

        external = ExternalEmployerInfo.objects.get(pk=practice.external_employer.pk)
        self.assertEqual(external.name, "Externí Firma s.r.o.")
        self.assertEqual(external.ico, "12345678")
        self.assertEqual(external.address, "Náměstí 1, Praha")
        self.assertEqual(external.contact_phone, "+420123456789")

    # ===========================================================================
    # C3.10 — Employer cannot delete practice with active applications
    # ===========================================================================

    def test_employer_cannot_delete_practice_with_active_applications(self):
        """C3.10: Cannot delete a practice that has active student applications."""
        # Create an active application on the practice
        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            is_cancelled=False,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )

        self.client.force_authenticate(user=self.org_user)
        url = f"/api/practices/employer/{self.practice.practice_id}/"

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active applications", str(response.data.get("detail", "")))

        # Practice should still exist (not hard-deleted)
        self.practice.refresh_from_db()
        self.assertTrue(Practice.objects.filter(pk=self.practice.practice_id).exists())

    def test_employer_can_soft_delete_empty_practice(self):
        """C3.10: Employer can soft-delete a practice with no active applications."""
        self.client.force_authenticate(user=self.org_user)
        url = f"/api/practices/employer/{self.practice.practice_id}/"

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Practice should be soft-deleted (is_active=False, is_cancelled=True)
        self.practice.refresh_from_db()
        self.assertFalse(self.practice.is_active)
        self.assertTrue(self.practice.is_cancelled)
        self.assertIsNotNone(self.practice.cancelled_at)
