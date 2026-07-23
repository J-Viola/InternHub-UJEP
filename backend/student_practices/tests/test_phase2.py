from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from practices.models import Practice, PracticeWorkflowState
from student_practices.models import Evaluation, StudentPractice, StudentPracticeWorkflowState
from users.models import ApprovalStatus, EmployerProfile, StudentUser


class Phase2Tests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = StudentUser.objects.create_user(
            email="student_p2@example.com",
            password="Password123!",
            first_name="Jan",
            last_name="Novák",
        )
        self.employer = EmployerProfile.objects.create(
            company_name="Test Corp",
            ico="12345678",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.practice = Practice.objects.create(
            title="Python Developer Intern",
            description="Test practice",
            employer=self.employer,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            progress_status=1,
            approval_status=ApprovalStatus.APPROVED,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=90),
        )
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            workflow_state=StudentPracticeWorkflowState.ENDED,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

    def test_dashboard_stats_endpoint(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/dashboard/stats/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("total_active", res.data)
        self.assertIn("state_counts", res.data)

    def test_data_export_endpoint_xlsx(self):
        from api.export_service import ExportService
        from student_practices.models import StudentPractice

        qs = StudentPractice.objects.filter(is_cancelled=False)
        xlsx_bytes = ExportService.generate_xlsx(qs)
        self.assertTrue(len(xlsx_bytes) > 0)

    def test_data_export_endpoint_csv(self):
        from api.export_service import ExportService
        from student_practices.models import StudentPractice

        qs = StudentPractice.objects.filter(is_cancelled=False)
        csv_content = ExportService.generate_csv(qs)
        self.assertIn("ID prihlasky", csv_content)

    def test_evaluation_submission(self):
        self.client.force_authenticate(user=self.student)
        payload = {
            "student_practice_id": self.sp.student_practice_id,
            "expertise_rating": 5,
            "expertise_comment": "Excellent skills",
            "communication_rating": 4,
            "communication_comment": "Good communication",
            "initiative_rating": 5,
            "initiative_comment": "High initiative",
            "overall_comment": "Overall great student",
        }
        res = self.client.post("/api/student-practices/evaluations/", payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Evaluation.objects.filter(student_practice=self.sp).exists())

    def test_confirm_contract_endpoint(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(f"/api/student-practices/{self.sp.student_practice_id}/confirm-contract/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertIsNotNone(self.sp.contract_received_date)
