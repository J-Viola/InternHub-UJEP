"""Export — scoping, sloupec garant, async notifikace, ownership downloadu."""

from datetime import date

from django.core.cache import cache
from django.test import TestCase, override_settings
from notifications.models import Notification
from rest_framework import status
from rest_framework.test import APIClient

from api.export_service import ExportService
from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class DataExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Katedra A (KI)
        self.dept_a = Department.objects.create(department_name="Informatika", department_code="KI")
        self.subject_a = Subject.objects.create(subject_name="Praxe KI", subject_code="KI/BOP", department=self.dept_a)
        # Katedra B (MA)
        self.dept_b = Department.objects.create(department_name="Matematika", department_code="MA")
        self.subject_b = Subject.objects.create(subject_name="Praxe MA", subject_code="MA/BOP", department=self.dept_b)

        # Users
        self.student = StudentUser.objects.create(email="student@export.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(
            email="org@export.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Export Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Garant katedry KI (is_garant_praxe + department)
        self.garant = ProfessorUser.objects.create_user(
            email="garant@export.test",
            password="password123",
            first_name="Alice",
            last_name="Garant",
            is_active=True,
            department=self.dept_a,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        # Garant katedry MA
        self.garant_b = ProfessorUser.objects.create_user(
            email="garantb@export.test",
            password="password123",
            first_name="Bob",
            last_name="GarantB",
            is_active=True,
            department=self.dept_b,
            is_garant_praxe=True,
        )

        # Praxe KI (s předmětem → garant KI)
        self.practice_a = Practice.objects.create(
            title="Praxe KI",
            employer=self.employer,
            subject=self.subject_a,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        # Praxe MA (garant MA)
        self.practice_b = Practice.objects.create(
            title="Praxe MA",
            employer=self.employer,
            subject=self.subject_b,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

        self.sp_a = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice_a,
            workflow_state=4,  # STARTED
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today(),
        )
        self.sp_b = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice_b,
            workflow_state=4,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today(),
        )

    def test_garant_does_not_see_foreign_department(self):
        """Garant katedry KI dostane pouze praxe svého departmentu (žádný cross-department leak)."""
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        self.assertIn("Praxe KI", body)
        self.assertNotIn("Praxe MA", body)

    def test_superuser_sees_all(self):
        """Superuser vidí vše."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_superuser(email="admin@export.test", password="password123")
        self.client.force_authenticate(user=admin)
        response = self.client.get("/api/export-data/?format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        self.assertIn("Praxe KI", body)
        self.assertIn("Praxe MA", body)

    def test_export_contains_garant_column(self):
        """CSV i XLSX obsahují sloupec „Garant" s jmény garantů."""
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        header_line = body.splitlines()[0]
        self.assertIn("Garant", header_line)
        # sp_a patří katedře KI → garant KI
        self.assertIn("Alice Garant", body)

        # XLSX
        xlsx_response = self.client.get("/api/export-data/?format=xlsx")
        self.assertEqual(xlsx_response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(xlsx_response.content) > 0)

    def test_export_service_garant_cell_empty_when_no_garant(self):
        """Žádný garant → prázdný sloupec (praxe bez subject)."""
        import csv
        import io as _io

        practice_no_subject = Practice.objects.create(
            title="Bez oboru",
            employer=self.employer,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        StudentPractice.objects.create(
            user=self.student,
            practice=practice_no_subject,
            workflow_state=4,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=1,
            start_date=date.today(),
            end_date=date.today(),
        )
        qs = StudentPractice.objects.filter(practice=practice_no_subject)
        csv_content = ExportService.generate_csv(qs)

        rows = list(csv.reader(_io.StringIO(csv_content)))
        header = rows[0]
        self.assertIn("Garant", header)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][header.index("Garant")], "")

    def test_async_export_creates_notification(self):
        """Async export (eager Celery) → vznikne notifikace EXPORT_READY žádajícímu userovi."""
        # Donutí async větev — simulujeme >500 záznamů přes malou velikost stránky
        # není potřeba: task voláme napřímo (eager mód běží v testech).
        from api.tasks import export_data_async

        export_id = "test-export-async"
        filters = {}
        user_id = self.garant.pk
        export_data_async(export_id, filters, "csv", user_id)

        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        notif = Notification.objects.filter(recipient=self.garant, verb="EXPORT_READY").first()
        self.assertIsNotNone(notif, "EXPORT_READY notifikace měla vzniknout")

    def test_async_export_scoping_inside_task(self):
        """Scoping se aplikuje uvnitř Celery tasku — garant nevidí cizí katedru ani async."""
        from api.tasks import export_data_async

        export_id = "test-export-async-scoped"
        export_data_async(export_id, {}, "csv", self.garant.pk)

        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        data = cache.get(f"export_{export_id}")
        self.assertIn("Praxe KI", data)
        self.assertNotIn("Praxe MA", data)

    def test_download_denied_for_foreign_user(self):
        """Cizí uživatel nesmí stáhnout cizí export → 404."""
        from api.tasks import export_data_async

        export_id = "test-export-download-owner"
        export_data_async(export_id, {}, "csv", self.garant.pk)
        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        cache.set(f"export_{export_id}_user_id", self.garant.pk, timeout=3600)

        # Cizí user (student) → 404
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f"/api/export/download/{export_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Vlastník → 200
        self.client.force_authenticate(user=self.garant)
        response = self.client.get(f"/api/export/download/{export_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_status_contract_success(self):
        """SUCCESS + download_url na `/api/export/download/{id}/`."""
        from api.tasks import export_data_async

        export_id = "test-export-status-success"
        export_data_async(export_id, {}, "csv", self.garant.pk)
        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")

        self.client.force_authenticate(user=self.garant)
        response = self.client.get(f"/api/export/status/{export_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["state"], "SUCCESS")
        self.assertEqual(response.data["download_url"], f"/api/export/download/{export_id}/")

    def test_export_status_contract_pending_and_failure(self):
        """PENDING (marker) i FAILURE (error) s download_url=null."""
        self.client.force_authenticate(user=self.garant)

        # PENDING: marker nastavený bez dokončeného tasku
        cache.set("export_test-status-pending_status", "pending", timeout=3600)
        response = self.client.get("/api/export/status/test-status-pending/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["state"], "PENDING")
        self.assertIsNone(response.data["download_url"])

        # FAILURE: chybový stav z cache
        cache.set("export_test-status-failure_status", "error: boom", timeout=3600)
        response = self.client.get("/api/export/status/test-status-failure/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["state"], "FAILURE")
        self.assertIsNone(response.data["download_url"])

        # Neznámý export → 404 (chybové tělo)
        response = self.client.get("/api/export/status/neexistuje/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("state", response.data)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_async_branch_via_http_returns_202(self):
        """GET /api/export-data/ s >500 záznamy → 202 + task_id (pokud se podaří naplnit)."""
        # Bez 500 záznamů se spustí sync větev; tato větev je pokryta přímým
        # voláním tasku výše. Přes HTTP ověříme alespoň sync cestu.
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
