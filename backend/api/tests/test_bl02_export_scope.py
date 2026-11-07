"""BL-02 — export fail-closed scope + status filter regression tests (audit BE-003).

Defect area: GET /api/export-data/ (sync CSV/XLSX + async task) + /api/export/status/.

- Prázdný scope (student bez předmětu, organizace bez profilu, neznámá role)
  → 403 / prázdný výsledek, NIKDY globální export (baseline: 200 + cizí e-maily).
- Status filtr (workflow_state) musí být respektován; prázdný/neplatný → 400.
- Cizí uživatel nedostane stav exportu ani download_url.
- Async task se scopuje vždy (fail-closed).

Vše syntetické; běh izolovanými test settings (viz audit COMMANDS.md).
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubject,
    UserSubjectType,
)

STARTED_MARKER = "started@bl02.test"
APPLIED_MARKER = "applied@bl02.test"
FOREIGN_DEPT_MARKER = "foreign-dept@bl02.test"


class DataExportScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.dept_a = Department.objects.create(department_name="BL02 Informatika", department_code="ZKI")
        self.dept_b = Department.objects.create(department_name="BL02 Matematika", department_code="ZMA")
        self.subject_a = Subject.objects.create(subject_name="BL02 Praxe KI", subject_code="ZKI/BOP", department=self.dept_a)
        self.subject_b = Subject.objects.create(subject_name="BL02 Praxe MA", subject_code="ZMA/BOP", department=self.dept_b)

        # Dvě organizace (každá praxe jiný employer → org scope je oddělitelný)
        self.org_user = OrganizationUser.objects.create(email="org-a@bl02.test", is_active=True, organization_role=OrganizationRole.OWNER)
        self.employer_a = EmployerProfile.objects.create(
            employer_id=self.org_user.pk, company_name="BL02 Org A", approval_status=ApprovalStatus.APPROVED
        )
        self.org_user.employer_profile = self.employer_a
        self.org_user.save()

        self.org_b = OrganizationUser.objects.create(email="org-b@bl02.test", is_active=True, organization_role=OrganizationRole.OWNER)
        self.employer_b = EmployerProfile.objects.create(
            employer_id=self.org_b.pk, company_name="BL02 Org B", approval_status=ApprovalStatus.APPROVED
        )
        self.org_b.employer_profile = self.employer_b
        self.org_b.save()

        # Organizace bez employer profilu (prázdný scope)
        self.org_without_profile = OrganizationUser.objects.create(
            email="org-no-profile@bl02.test", is_active=True, organization_role=OrganizationRole.OWNER
        )

        # Studenti
        self.student_no_subjects = StudentUser.objects.create(
            email="no-subjects@bl02.test", first_name="BL02", last_name="NoSubject", is_active=True
        )
        self.student_with_subject = StudentUser.objects.create(
            email="with-subject@bl02.test", first_name="BL02", last_name="WithSubject", is_active=True
        )
        UserSubject.objects.create(user=self.student_with_subject, subject=self.subject_a, role=UserSubjectType.Student)

        self.started_student = StudentUser.objects.create(email=STARTED_MARKER, first_name="BL02", last_name="Started", is_active=True)
        self.applied_student = StudentUser.objects.create(email=APPLIED_MARKER, first_name="BL02", last_name="Applied", is_active=True)
        self.foreign_dept_student = StudentUser.objects.create(
            email=FOREIGN_DEPT_MARKER, first_name="BL02", last_name="ForeignDept", is_active=True
        )

        # Garant katedry KI + admin + neznámá (plain) role
        self.garant = ProfessorUser.objects.create_user(
            email="garant@bl02.test",
            password="bl02-only-password",
            first_name="BL02",
            last_name="Garant",
            is_active=True,
            department=self.dept_a,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.admin = get_user_model().objects.create_superuser(email="admin@bl02.test", password="bl02-only-password")
        self.plain_user = get_user_model().objects.create_user(email="plain-role@bl02.test", password="bl02-only-password", is_active=True)

        self.practice_a = Practice.objects.create(
            title="BL02 Praxe KI",
            employer=self.employer_a,
            subject=self.subject_a,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=10,
        )
        self.practice_b = Practice.objects.create(
            title="BL02 Praxe MA",
            employer=self.employer_b,
            subject=self.subject_b,
            start_date=date.today(),
            end_date=date.today(),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=10,
        )

        self.sp_started = self._make_sp(self.started_student, self.practice_a, StudentPracticeWorkflowState.STARTED)
        self.sp_applied = self._make_sp(self.applied_student, self.practice_a, StudentPracticeWorkflowState.APPLIED)
        self.sp_foreign_dept = self._make_sp(self.foreign_dept_student, self.practice_b, StudentPracticeWorkflowState.STARTED)
        # Vlastní přihláška studenta s předmětem — jeho PŘESNÁ autorizovaná množina
        self.sp_student_own = self._make_sp(self.student_with_subject, self.practice_a, StudentPracticeWorkflowState.STARTED)

    def _make_sp(self, user, practice, state):
        return StudentPractice.objects.create(
            user=user,
            practice=practice,
            workflow_state=state,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today(),
        )

    def _exported_ids(self, response):
        """Přesná množina exportovaných ID (sloupec „ID přihlášky“)."""
        import csv as _csv
        import io as _io

        rows = list(_csv.reader(_io.StringIO(response.content.decode("utf-8"))))
        ids = set()
        for row in rows[1:]:
            if row and row[0].strip().isdigit():
                ids.add(int(row[0].strip()))
        return ids

    # ------------------------------------------------------------------
    # Fail-closed: prázdný scope → 403, nikdy globální export (BE-003)
    # ------------------------------------------------------------------

    def test_student_without_subjects_csv_denied(self):
        """Audit probe BE-003: student bez UserSubject → 403, žádný cizí řádek."""
        self.client.force_authenticate(user=self.student_no_subjects)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)
        self.assertNotIn(FOREIGN_DEPT_MARKER.encode(), response.content)

    def test_student_without_subjects_xlsx_denied(self):
        self.client.force_authenticate(user=self.student_no_subjects)
        response = self.client.get("/api/export-data/?format=xlsx")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    def test_unknown_role_denied(self):
        """Neznámá role (plain User) — dříve (None, None) = neomezený export."""
        self.client.force_authenticate(user=self.plain_user)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    def test_org_without_profile_denied(self):
        self.client.force_authenticate(user=self.org_without_profile)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    # ------------------------------------------------------------------
    # Oprávněné rozsahy zůstávají funkční (žádná regrese kvalifikovaných rolí)
    # ------------------------------------------------------------------

    def test_student_export_exact_own_ids_only(self):
        """MAJOR-2: přesná autorizovaná množina studenta = jen jeho vlastní
        přihlášky; žádní vrstevníci z katedry."""
        self.client.force_authenticate(user=self.student_with_subject)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._exported_ids(response), {self.sp_student_own.student_practice_id})
        body = response.content.decode("utf-8")
        self.assertIn("with-subject@bl02.test", body)  # vlastní řádek
        self.assertNotIn(STARTED_MARKER, body)  # vrstevník z katedry NE
        self.assertNotIn(APPLIED_MARKER, body)
        self.assertNotIn(FOREIGN_DEPT_MARKER, body)

    def test_org_scoped_to_own_practices(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 200)
        # Přesná množina = přihlášky praxí vlastního employer profilu
        self.assertEqual(
            self._exported_ids(response),
            {
                self.sp_started.student_practice_id,
                self.sp_applied.student_practice_id,
                self.sp_student_own.student_practice_id,
            },
        )
        body = response.content.decode("utf-8")
        self.assertNotIn(FOREIGN_DEPT_MARKER, body)

    def test_superuser_sees_all(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._exported_ids(response),
            {
                self.sp_started.student_practice_id,
                self.sp_applied.student_practice_id,
                self.sp_foreign_dept.student_practice_id,
                self.sp_student_own.student_practice_id,
            },
        )

    # ------------------------------------------------------------------
    # Status filtr musí být respektován; prázdný/neplatný → fail-closed 400
    # ------------------------------------------------------------------

    def test_status_filter_respected(self):
        self.client.force_authenticate(user=self.garant)
        response = self.client.get(f"/api/export-data/?format=csv&workflow_state={StudentPracticeWorkflowState.STARTED.value}")

        self.assertEqual(response.status_code, 200)
        # Přesná množina: STARTED na katedře KI (APPLIED i cizí katedra vyfiltrovány)
        self.assertEqual(
            self._exported_ids(response),
            {
                self.sp_started.student_practice_id,
                self.sp_student_own.student_practice_id,
            },
        )
        body = response.content.decode("utf-8")
        self.assertNotIn(APPLIED_MARKER, body)  # jiný stav → filtrováno
        self.assertNotIn(FOREIGN_DEPT_MARKER, body)  # cizí katedra → mimo scope

    def test_blank_status_filter_denied(self):
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv&workflow_state=")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    def test_invalid_status_filter_denied(self):
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv&workflow_state=abc")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    def test_out_of_range_status_filter_denied(self):
        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/export-data/?format=csv&workflow_state=99")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(STARTED_MARKER.encode(), response.content)

    # ------------------------------------------------------------------
    # Status endpoint: cizí uživatel nedostane stav/download_url
    # ------------------------------------------------------------------

    def test_export_status_denied_for_foreign_user(self):
        from api.tasks import export_data_async

        export_id = "bl02-status-foreign"
        export_data_async(export_id, {}, "csv", self.garant.pk)
        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        cache.set(f"export_{export_id}_user_id", self.garant.pk, timeout=3600)

        # Cizí uživatel → stejná odpověď jako u neexistujícího exportu
        self.client.force_authenticate(user=self.student_no_subjects)
        foreign_response = self.client.get(f"/api/export/status/{export_id}/")
        self.assertEqual(foreign_response.status_code, 404)
        self.assertIsNone(foreign_response.data.get("download_url"))

        # Vlastník → 200 SUCCESS
        self.client.force_authenticate(user=self.garant)
        owner_response = self.client.get(f"/api/export/status/{export_id}/")
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.data["state"], "SUCCESS")

    def test_export_status_denied_when_owner_marker_missing(self):
        """MAJOR-3: bez doloženého vlastnictví status zamítnut (fail-closed);
        privilegovaná role projde."""
        # Jen status marker, žádný owner marker — vlastnictví nedoloženo
        cache.set("export_bl02-no-owner-marker_status", "completed", timeout=3600)

        self.client.force_authenticate(user=self.garant)
        denied = self.client.get("/api/export/status/bl02-no-owner-marker/")
        self.assertEqual(denied.status_code, 404)
        self.assertIsNone(denied.data.get("download_url"))

        # Explicitně privilegovaná role (superuser) → povoleno
        self.client.force_authenticate(user=self.admin)
        allowed = self.client.get("/api/export/status/bl02-no-owner-marker/")
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data["state"], "SUCCESS")

    # ------------------------------------------------------------------
    # Async task: fail-closed scoping i mimo HTTP view
    # ------------------------------------------------------------------

    def test_async_export_empty_scope_produces_no_rows(self):
        from api.tasks import export_data_async

        export_id = "bl02-async-empty-scope"
        export_data_async(export_id, {}, "csv", self.student_no_subjects.pk)

        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        data = cache.get(f"export_{export_id}")
        self.assertIsNotNone(data)
        self.assertIn("ID přihlášky", data)  # hlavička CSV
        self.assertNotIn(STARTED_MARKER, data)  # žádný cizí řádek
        self.assertNotIn(FOREIGN_DEPT_MARKER, data)

    def test_async_export_scoped_to_garant_department(self):
        from api.tasks import export_data_async

        export_id = "bl02-async-garant-scope"
        export_data_async(export_id, {}, "csv", self.garant.pk)

        self.assertEqual(cache.get(f"export_{export_id}_status"), "completed")
        data = cache.get(f"export_{export_id}")
        self.assertIn(STARTED_MARKER, data)
        self.assertNotIn(FOREIGN_DEPT_MARKER, data)
