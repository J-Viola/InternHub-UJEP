from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from api.export_service import _escape_formula_cell
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
from users.models import ApprovalStatus, EmployerProfile, OrganizationRole, OrganizationUser, StudentUser


class ExportRF21BTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_a = OrganizationUser.objects.create(email="rf21b-a@example.test", is_active=True, organization_role=OrganizationRole.OWNER)
        self.org_b = OrganizationUser.objects.create(email="rf21b-b@example.test", is_active=True, organization_role=OrganizationRole.OWNER)
        self.employer_a = EmployerProfile.objects.create(
            employer_id=self.org_a.pk, company_name="RF21B Firma Alfa", approval_status=ApprovalStatus.APPROVED
        )
        self.employer_b = EmployerProfile.objects.create(
            employer_id=self.org_b.pk, company_name="RF21B Firma Beta", approval_status=ApprovalStatus.APPROVED
        )
        self.org_a.employer_profile = self.employer_a
        self.org_a.save()
        self.student_a = StudentUser.objects.create(
            email="rf21b-student-a@example.test", first_name="Eva", last_name="Alfa", is_active=True
        )
        self.student_b = StudentUser.objects.create(
            email="rf21b-student-b@example.test", first_name="Jan", last_name="Beta", is_active=True
        )
        self.practice_a = self._practice(self.employer_a, "RF21B Alfa")
        self.practice_b = self._practice(self.employer_b, "RF21B Beta")
        self.sp_a = self._application(self.student_a, self.practice_a)
        self.sp_b = self._application(self.student_b, self.practice_b)

    @staticmethod
    def _practice(employer, title):
        return Practice.objects.create(
            title=title,
            employer=employer,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=2,
        )

    @staticmethod
    def _application(student, practice):
        return StudentPractice.objects.create(
            user=student,
            practice=practice,
            start_date=practice.start_date,
            end_date=practice.end_date,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=0,
            year=2025,
        )

    def _ids(self, response):
        return response.content.decode("utf-8-sig")

    def test_employer_and_student_exports_are_scoped_and_filters_are_applied(self):
        self.client.force_authenticate(self.org_a)
        org_response = self.client.get("/api/export-data/?format=csv&institution=Alfa")
        self.assertEqual(org_response.status_code, 200)
        self.assertIn("RF21B Alfa", self._ids(org_response))
        self.assertNotIn("RF21B Beta", self._ids(org_response))
        self.assertIn("Akademický rok", self._ids(org_response))

        self.client.force_authenticate(self.student_a)
        student_response = self.client.get("/api/export-data/?format=csv")
        self.assertEqual(student_response.status_code, 200)
        self.assertIn("RF21B Alfa", self._ids(student_response))
        self.assertNotIn("RF21B Beta", self._ids(student_response))

    def test_employer_id_filter_limits_count(self):
        from api.export_service import ExportService

        self.assertEqual(ExportService.get_count({"employer_id": self.employer_a.pk}, dept_ids=None), 1)

    def test_formula_escape_handles_leading_whitespace(self):
        for value in (" =1+1", "\n=1+1", "\r\t@SUM(A1:A2)", "  -1+2"):
            with self.subTest(value=value):
                self.assertEqual(_escape_formula_cell(value), f"'{value}")
