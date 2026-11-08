"""L1 — matice oprávnění (role × endpoint), testovací plán kap. 5.8.

Testy jsou plně syntetické (žádná demo data) a sdílejí fixture
``BL02FixtureMixin`` (dva studenti, dvě organizace, garant a profesor jiné
katedry), stejně jako ``test_file_access.py`` a ``test_bl02_authorization.py``.

Pokryté řádky matice:
1. nepřihlášený → chráněné endpointy vrací 401/403,
2. student A → karta, dokumenty ani hodnocení studenta B,
3. organizace A → PUT/PATCH/DELETE inzerátu organizace B,
4. organizace A → detail cizího neaktivního inzerátu je zkrácený,
5. neschválená organizace → create/edit inzerátu je 403 EMPLOYER_NOT_APPROVED,
6. profesor jiné katedry → přihlášky ani export cizí katedry,
7. student → endpointy garanta (transition, dashboard) vrací 403; export studenta
   je own-scope (200 s vlastními řádky, 403 bez přihlášek — MAJOR-2),
8. refresh cookie smazaného uživatele → 401.

Poznámka k nálezům: testy, které úmyslně porovnávají matici L1 s aktuální
implementací, jsou v docstringu označené jako ``NÁLEZ``. Pokud v produkčním
kódu chybí guard, test záměrně selže a chyba se opravuje mimo tento soubor.
"""

from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    Evaluation,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from student_practices.tests.test_bl02_authorization import BL02FixtureMixin
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
)

# E-mail studenta B z BL02 fixture — slouží jako sentinel v cizích odpovědích.
FOREIGN_STUDENT_EMAIL = "foreign-student@bl02.test"
# Sentinel v hodnocení studenta B; nesmí se objevit v odpovědi studenta A.
EVALUATION_SENTINEL = "L1_SYNTHETIC_EVALUATION_SENTINEL"


class PermissionMatrixUATTests(BL02FixtureMixin, TestCase):
    """Matice oprávnění L1 nad syntetickou BL02 fixture."""

    # ------------------------------------------------------------------
    # Pomocné fabriky
    # ------------------------------------------------------------------

    def _make_practice(self, *, employer, title, is_active=True, description="L1 popis", responsibilities="L1 odpovědnosti"):
        """Vytvoří inzerát přímo přes ORM (bez HTTP), aby test nezávisel na seedu."""
        return Practice.objects.create(
            title=title,
            description=description,
            responsibilities=responsibilities,
            employer=employer,
            subject=self.subject,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=is_active,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=10,
        )

    def _make_sp_with_contract_document(self, user):
        """Přihláška ve stavu ENDED s reálně uloženým souborem smlouvy."""
        sp = self.make_sp(user, state=StudentPracticeWorkflowState.ENDED)
        document = UploadedDocument.objects.create(
            document=SimpleUploadedFile("l1_contract.pdf", b"%PDF-1.4 l1 synthetic", content_type="application/pdf"),
            uploaded_at=timezone.now(),
            document_type=DocumentType.CONTRACT,
            status=DocumentStatus.PENDING,
        )
        sp.contract_document = document
        sp.save(update_fields=["contract_document"])
        return sp, document

    def _response_items(self, response):
        """Pomocník pro stránkovaný i nestránkovaný seznam odpovědí."""
        data = response.data
        if isinstance(data, dict):
            return data.get("results", [])
        return data

    def _exported_ids(self, response):
        """Přesná množina exportovaných ID (sloupec „ID přihlášky“ v CSV)."""
        import csv as _csv
        import io as _io

        rows = list(_csv.reader(_io.StringIO(response.content.decode("utf-8"))))
        ids = set()
        for row in rows[1:]:
            if row and row[0].strip().isdigit():
                ids.add(int(row[0].strip()))
        return ids

    # ------------------------------------------------------------------
    # 1) Nepřihlášený uživatel
    # ------------------------------------------------------------------

    def test_unauthenticated_protected_endpoints_return_401_or_403(self):
        """L1 řádek 1: anonym nesmí na chráněné API endpointy (401/403, nikdy 200)."""
        anonymous = APIClient()
        for url in (
            "/api/practices/employer/",
            "/api/student-practices/professor-applications/",
            "/api/export-data/?format=csv",
        ):
            with self.subTest(url=url):
                response = anonymous.get(url)
                self.assertIn(
                    response.status_code,
                    (401, 403),
                    msg=f"Anonym na {url} dostal {response.status_code}, očekáváno 401/403.",
                )

    # ------------------------------------------------------------------
    # 2) Student A nesmí číst data studenta B
    # ------------------------------------------------------------------

    def test_student_a_cannot_read_student_b_card_documents_or_evaluation(self):
        """L1 řádek 2: cizí student nesmí číst kartu, dokumenty ani hodnocení.

        Karta a dokument mají vracet 403/404; detail hodnocení je mimo
        scoped queryset → 404. Sentinel se nesmí objevit v žádné odpovědi.
        """
        sp, document = self._make_sp_with_contract_document(self.foreign_student)
        evaluation = Evaluation.objects.create(
            student_practice=sp,
            expertise_comment=EVALUATION_SENTINEL,
            evaluated_by=self.garant,
        )

        self.client.force_authenticate(user=self.student_owner)

        urls = {
            "karta": f"/api/student-practices/{sp.student_practice_id}",
            "dokument": f"/api/student-practices/download-document/{document.document_id}",
            "hodnocení": f"/api/student-practices/evaluations/{evaluation.evaluation_id}/",
        }
        for name, url in urls.items():
            with self.subTest(cast=name):
                response = self.client.get(url)
                self.assertIn(
                    response.status_code,
                    (403, 404),
                    msg=f"Student A na {name} studenta B dostal {response.status_code}, očekáváno 403/404.",
                )
                self.assertNotIn(EVALUATION_SENTINEL.encode(), response.content)

    # ------------------------------------------------------------------
    # 3) Organizace A nesmí mutovat inzerát organizace B
    # ------------------------------------------------------------------

    def test_org_a_cannot_mutate_org_b_practice(self):
        """L1 řádek 3: PUT/PATCH/DELETE cizího inzerátu → 403/404 bez mutace."""
        practice = self._make_practice(employer=self.foreign_employer, title="L1 inzerát organizace B")
        url = f"/api/practices/employer/{practice.practice_id}/"
        self.client.force_authenticate(user=self.org_user)

        for method in ("put", "patch", "delete"):
            with self.subTest(method=method.upper()):
                if method == "delete":
                    response = self.client.delete(url)
                else:
                    response = getattr(self.client, method)(url, {"title": "L1 HACKED"}, format="json")

                self.assertIn(
                    response.status_code,
                    (403, 404),
                    msg=f"Organizace A {method.upper()} cizího inzerátu dostala {response.status_code}, očekáváno 403/404.",
                )
                practice.refresh_from_db()
                self.assertEqual(practice.title, "L1 inzerát organizace B")
                self.assertTrue(Practice.objects.filter(pk=practice.pk).exists())

    # ------------------------------------------------------------------
    # 4) Zkrácený detail cizího neaktivního inzerátu
    # ------------------------------------------------------------------

    def test_foreign_org_gets_redacted_inactive_practice_detail_owner_gets_full(self):
        """L1 řádek 4: cizí organizace nesmí vidět description/responsibilities."""
        practice = self._make_practice(
            employer=self.foreign_employer,
            title="L1 neaktivní inzerát organizace B",
            is_active=False,
            description="L1_TAJNY_POPIS",
            responsibilities="L1_TAJNE_ODPOVEDNOSTI",
        )
        url = f"/api/practices/employer/{practice.practice_id}/"

        self.client.force_authenticate(user=self.org_user)
        foreign = self.client.get(url)
        self.assertEqual(foreign.status_code, 200)
        self.assertNotIn("description", foreign.data)
        self.assertNotIn("responsibilities", foreign.data)
        self.assertNotIn(b"L1_TAJNY_POPIS", foreign.content)
        self.assertNotIn(b"L1_TAJNE_ODPOVEDNOSTI", foreign.content)

        self.client.force_authenticate(user=self.foreign_org)
        owner = self.client.get(url)
        self.assertEqual(owner.status_code, 200)
        self.assertEqual(owner.data.get("description"), "L1_TAJNY_POPIS")
        self.assertEqual(owner.data.get("responsibilities"), "L1_TAJNE_ODPOVEDNOSTI")

    # ------------------------------------------------------------------
    # 5) Neschválená organizace nesmí vytvořit ani editovat inzerát
    # ------------------------------------------------------------------

    def test_unapproved_organization_cannot_create_or_edit_practice(self):
        """L1 řádek 5: PENDING organizace → create i edit 403 EMPLOYER_NOT_APPROVED."""
        pending_org = OrganizationUser.objects.create(
            email="pending-matrix@l1.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        pending_profile = EmployerProfile.objects.create(
            employer_id=pending_org.pk,
            company_name="L1 Pending Org",
            approval_status=ApprovalStatus.PENDING,
        )
        pending_org.employer_profile = pending_profile
        pending_org.save(update_fields=["employer_profile"])

        own_practice = self._make_practice(employer=pending_profile, title="L1 inzerát čekající organizace")
        self.client.force_authenticate(user=pending_org)

        create_payload = {
            "subject_id": self.subject.subject_id,
            "title": "L1 nová nabídka",
            "description": "L1 popis",
            "responsibilities": "L1 odpovědnosti",
            "mentor_name": "L1 Mentor",
            "contact_email": "mentor@l1.test",
            "start_date": (date.today() + timedelta(days=10)).strftime("%d.%m.%Y"),
        }

        with self.subTest(akce="create"):
            response = self.client.post("/api/practices/employer/", create_payload, format="json")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data.get("error_code"), "EMPLOYER_NOT_APPROVED")
            self.assertFalse(Practice.objects.filter(title="L1 nová nabídka").exists())

        with self.subTest(akce="edit"):
            response = self.client.patch(
                f"/api/practices/employer/{own_practice.practice_id}/",
                {"title": "L1 HACKED"},
                format="json",
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data.get("error_code"), "EMPLOYER_NOT_APPROVED")
            own_practice.refresh_from_db()
            self.assertEqual(own_practice.title, "L1 inzerát čekající organizace")

    # ------------------------------------------------------------------
    # 6) Profesor jiné katedry nedostane data cizí katedry
    # ------------------------------------------------------------------

    def test_foreign_professor_gets_no_foreign_department_applications_or_export(self):
        """L1 řádek 6: aplikace i export profesora jiné katedry jsou prázdné/403.

        Přihláška studenta B leží v katedře A; profesor jiné katedry ji nesmí
        dostat ani v seznamu přihlášek, ani v exportu.
        """
        self.make_sp(self.foreign_student, state=StudentPracticeWorkflowState.APPLIED)

        self.client.force_authenticate(user=self.foreign_professor)

        applications = self.client.get("/api/student-practices/professor-applications/")
        self.assertIn(applications.status_code, (200, 403))
        if applications.status_code == 200:
            self.assertEqual(list(self._response_items(applications)), [])
        self.assertNotIn(FOREIGN_STUDENT_EMAIL.encode(), applications.content)

        export = self.client.get("/api/export-data/?format=csv")
        self.assertIn(export.status_code, (200, 403))
        self.assertNotIn(FOREIGN_STUDENT_EMAIL.encode(), export.content)

    # ------------------------------------------------------------------
    # 7) Student nesmí na endpointy garanta
    # ------------------------------------------------------------------

    def test_student_is_denied_on_garant_endpoints(self):
        """L1 řádek 7: student → transition/dashboard musí dostat 403.

        Export je záměrně mimo tento seznam: F-14 / MAJOR-2 mu dává vlastní
        own-scope testy (200 s vlastními řádky, 403 bez přihlášek).
        """
        # Vlastní přihláška, aby transition i dashboard měly nad čím běžet.
        self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.APPLIED)
        self.client.force_authenticate(user=self.student_owner)

        cases = (
            (
                "transition",
                "post",
                f"/api/practices/{self.practice.practice_id}/transition/",
                {"target_state": PracticeWorkflowState.CONTENT_APPROVED.value},
            ),
            ("dashboard", "get", "/api/dashboard/stats/", None),
        )
        for name, method, url, payload in cases:
            with self.subTest(endpoint=name):
                if payload is None:
                    response = getattr(self.client, method)(url)
                else:
                    response = getattr(self.client, method)(url, payload, format="json")
                self.assertEqual(
                    response.status_code,
                    403,
                    msg=f"L1: student na endpointu garanta '{name}' dostal {response.status_code}, očekáváno 403.",
                )

    def test_student_export_is_own_scope(self):
        """F-14 / MAJOR-2: student s vlastní přihláškou → 200, jen vlastní řádky."""
        own_sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.APPLIED)
        foreign_sp = self.make_sp(self.foreign_student, state=StudentPracticeWorkflowState.APPLIED)

        self.client.force_authenticate(user=self.student_owner)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._exported_ids(response), {own_sp.student_practice_id})
        self.assertNotIn(foreign_sp.student_practice_id, self._exported_ids(response))
        self.assertNotIn(FOREIGN_STUDENT_EMAIL.encode(), response.content)

    def test_student_export_without_applications_is_denied(self):
        """F-14: student bez přihlášek → 403 (export je fail-closed při count == 0)."""
        self.client.force_authenticate(user=self.foreign_student)
        response = self.client.get("/api/export-data/?format=csv")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(FOREIGN_STUDENT_EMAIL.encode(), response.content)

    def test_vk_dashboard_returns_200(self):
        """P0-5 / F-13: VK (role vk / HEAD) projde na dashboard."""
        vk_role, _ = StagRole.objects.get_or_create(
            role=StagRoleEnum.VK,
            defaults={"role_name": "Vedoucí katedry (L1 test)"},
        )
        vk = ProfessorUser.objects.create_user(
            email="vk@bl02.test",
            password="bl02-only-password",
            first_name="BL02",
            last_name="VK",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            stag_role=vk_role,
        )

        self.client.force_authenticate(user=vk)
        response = self.client.get("/api/dashboard/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("total_active", response.data)

    def test_garant_dashboard_is_scoped_to_own_department(self):
        """P0-5 / F-13: garant katedry A nevidí at_risk_items praxe katedry B."""
        foreign_subject = Subject.objects.create(
            subject_name="BL02 MA praxe",
            subject_code="BL02/MAP",
            department=self.other_department,
            min_hours=480,
        )
        foreign_practice = Practice.objects.create(
            title="BL02 praxe katedry B",
            description="Syntetická praxe katedry B",
            employer=self.employer,
            subject=foreign_subject,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            available_positions=10,
        )
        foreign_sp = self.make_sp(
            self.foreign_student,
            practice=foreign_practice,
            state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
        )
        own_sp = self.make_sp(self.student_owner, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)

        self.client.force_authenticate(user=self.garant)
        response = self.client.get("/api/dashboard/stats/")

        self.assertEqual(response.status_code, 200)
        ids = {item["student_practice_id"] for item in response.data["at_risk_items"]}
        self.assertIn(own_sp.student_practice_id, ids)
        self.assertNotIn(foreign_sp.student_practice_id, ids)

    # ------------------------------------------------------------------
    # 8) Refresh cookie smazaného uživatele
    # ------------------------------------------------------------------

    def test_refresh_cookie_of_deleted_user_returns_401(self):
        """L1 řádek 8 / F-11: refresh token smazaného uživatele → 401, nikdy 500."""
        refresh_token = str(RefreshToken.for_user(self.foreign_student))
        self.foreign_student.delete()

        client = APIClient()
        client.cookies["refresh_token"] = refresh_token
        response = client.post("/api/users/token/refresh/")

        self.assertEqual(
            response.status_code,
            401,
            msg=f"Refresh smazaného uživatele vrátil {response.status_code}, očekáváno 401.",
        )
