"""BL-05 / RF-02a — filtr „typ úvazku" (employment type) v katalogu nabídek.

Požadavek (Tests/SRS/extracted/analysis.txt, RF-02a, L1558–L1561):
„Systém musí studentovi umožnit pokročilé filtrování a vyhledávání nabídek
praxí podle zadaných technologií, softwarových nástrojů, metodik a typu
úvazku." — atom RF-02a.04 (filtr dle typu úvazku) byl v auditu MISSING.

Kódy číselníku jsou ZÁVAZNÉ dle rozhodnutí garantů/vlastníka 2026-10-11
(audit/2026-10-04/lanes/guarantor-values.md §1, C21-A): numerická osa
„Úvazek 0,5" / „Úvazek 1,0". PLACEHOLDER kódy byly staženy datovou migrací
0014 (legacy mapping pokrytý testem níže).
"""

from datetime import date, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import (
    EMPLOYMENT_TYPE_CHOICES,
    EMPLOYMENT_TYPE_LEGACY_CODE_MAP,
    Practice,
    PracticeWorkflowState,
    ProgressStatus,
)
from subject.models import Subject
from users.models import ApprovalStatus, EmployerProfile, OrganizationRole, OrganizationUser, StudentUser

PART_TIME = "uvazek_0_5"
FULL_TIME = "uvazek_1_0"
# stažené PLACEHOLDER kódy (po migraci 0014 už nejsou v číselníku)
LEGACY_PART_TIME = "placeholder_part_time"
LEGACY_FULL_TIME = "placeholder_full_time"


class EmploymentTypeFilterTests(TestCase):
    """RF-02a.04 — student filtruje katalog nabídek podle typu úvazku."""

    def setUp(self):
        self.client = APIClient()

        self.org_user = OrganizationUser.objects.create(
            email="org-uvazek@test.com",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Uvazek Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.student = StudentUser.objects.create(
            email="student-uvazek@test.com",
            first_name="Student",
            last_name="One",
            is_active=True,
        )

        self.dept = Department.objects.create(department_name="IT", department_code="KI")
        self.subject = Subject.objects.create(subject_name="Java", department=self.dept)

        self.practice_part = self._make_practice("Nabídka 0,5", PART_TIME)
        self.practice_full = self._make_practice("Nabídka 1,0", FULL_TIME)
        self.practice_unspecified = self._make_practice("Nabídka bez úvazku", "")

    def _make_practice(self, title: str, employment_type: str) -> Practice:
        return Practice.objects.create(
            employer=self.employer,
            subject=self.subject,
            title=title,
            description="Popis",
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=100),
            is_active=True,
            employment_type=employment_type,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

    def _list_offers(self, query: str = ""):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f"/api/practices/student/{query}")
        return response

    @staticmethod
    def _titles(response):
        results = response.data["results"] if "results" in response.data else response.data
        return {item["title"] for item in results}

    # --- filtr -----------------------------------------------------------------

    def test_no_filter_returns_all_offers(self):
        response = self._list_offers()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._titles(response), {"Nabídka 0,5", "Nabídka 1,0", "Nabídka bez úvazku"})

    def test_filter_by_part_time_returns_only_matching_offers(self):
        response = self._list_offers(f"?employment_type={PART_TIME}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._titles(response), {"Nabídka 0,5"})
        self.assertEqual(response.data["results"][0]["practice_id"], self.practice_part.practice_id)

    def test_filter_by_full_time_returns_only_matching_offers(self):
        response = self._list_offers(f"?employment_type={FULL_TIME}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._titles(response), {"Nabídka 1,0"})
        self.assertEqual(response.data["results"][0]["practice_id"], self.practice_full.practice_id)

    def test_filter_combines_with_skills_search(self):
        # RF-02a pokrývá i technologie/nástroje/metodiky přes generické skills —
        # úvazkový filtr musí fungovat společně s ním (ne jako náhrada).
        self.practice_part.skills = ["Python", "Django"]
        self.practice_part.save(update_fields=["skills"])

        response = self._list_offers(f"?employment_type={PART_TIME}&skills=Django")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._titles(response), {"Nabídka 0,5"})

        response = self._list_offers(f"?employment_type={PART_TIME}&skills=Rust")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._titles(response), set())

    def test_unknown_employment_type_value_is_rejected(self):
        # Mimo číselník → 400 (datový kontrakt schvalují garanti, C21-A).
        response = self._list_offers("?employment_type=not_a_real_code")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_legacy_placeholder_codes_rejected_after_code_list_update(self):
        """PO migraci 0014: stažené PLACEHOLDER kódy už nejsou v číselníku → 400."""
        response = self._list_offers(f"?employment_type={LEGACY_PART_TIME}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_employment_type_value_is_ignored(self):
        response = self._list_offers("?employment_type=")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self._titles(response)), 3)

    def test_employment_type_exposed_in_list_payload(self):
        response = self._list_offers(f"?employment_type={PART_TIME}")
        self.assertEqual(response.data["results"][0].get("employment_type"), PART_TIME)

    # --- zápis (datový kontrakt nabídky) ---------------------------------------

    def _create_payload(self, employment_type: str | None = None) -> dict:
        payload = {
            "subject_id": self.subject.subject_id,
            "title": "Nová stáž",
            "description": "Popis",
            "responsibilities": "Odpovědnosti",
            "mentor_name": "Jan Mentor",
            "contact_email": "mentor@firma.cz",
            "start_date": (date.today() + timedelta(days=10)).strftime("%d.%m.%Y"),
        }
        if employment_type is not None:
            payload["employment_type"] = employment_type
        return payload

    def test_employer_create_persists_employment_type(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.post("/api/practices/employer/", self._create_payload(PART_TIME), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data.get("employment_type"), PART_TIME)

        created = Practice.objects.get(title="Nová stáž")
        self.assertEqual(created.employment_type, PART_TIME)

    def test_employer_create_rejects_unknown_employment_type(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.post("/api/practices/employer/", self._create_payload("not_a_real_code"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Practice.objects.filter(title="Nová stáž").exists())


class EmploymentTypeLegacyMappingTests(TestCase):
    """Legacy mapping (datová migrace 0014) — placeholder kódy → závazné kódy.

    Ověřuje rozhodnutí garantor-values.md §1: normalizace uložených
    placeholder_* hodnot na uvazek_0_5 / uvazek_1_0 (pre-production,
    reverzibilní). Test přímo volá mapovací funkci z migračního modulu —
    testovací settings má MIGRATION_MODULES vypnuté, takže by jinak
    migrace při běhu testů neběžela.
    """

    @staticmethod
    def _migration_module():
        import importlib

        return importlib.import_module("practices.migrations.0014_practice_employment_type_codes")

    def _make_practice(self, title: str, employment_type: str) -> Practice:
        dept = Department.objects.get_or_create(department_name="IT", defaults={"department_code": "KI"})[0]
        subject = Subject.objects.get_or_create(subject_name="Java", defaults={"department": dept})[0]
        employer = EmployerProfile.objects.create(
            company_name=f"Map Corp {title}",
            approval_status=ApprovalStatus.APPROVED,
        )
        return Practice.objects.create(
            employer=employer,
            subject=subject,
            title=title,
            description="Popis",
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=100),
            is_active=True,
            employment_type=employment_type,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

    def test_migration_map_matches_model_legacy_map(self):
        """Migrační mapa a modelová mapa se musí shodovat (jediný zdroj pravdy)."""
        module = self._migration_module()
        self.assertEqual(module.LEGACY_TO_CANONICAL, EMPLOYMENT_TYPE_LEGACY_CODE_MAP)
        self.assertEqual(set(module.LEGACY_TO_CANONICAL.values()), {code for code, _label in EMPLOYMENT_TYPE_CHOICES})

    def test_map_placeholder_codes_migrates_stored_values(self):
        """Uložené placeholder kódy → autoritativní kódy; prázdný úvazek beze změny."""
        module = self._migration_module()
        part = self._make_practice("Legacy 0,5", LEGACY_PART_TIME)
        full = self._make_practice("Legacy 1,0", LEGACY_FULL_TIME)
        empty = self._make_practice("Bez úvazku", "")

        module.apply_employment_type_map(Practice, module.LEGACY_TO_CANONICAL)

        part.refresh_from_db()
        full.refresh_from_db()
        empty.refresh_from_db()
        self.assertEqual(part.employment_type, "uvazek_0_5")
        self.assertEqual(full.employment_type, "uvazek_1_0")
        self.assertEqual(empty.employment_type, "")

    def test_unmap_restores_legacy_values(self):
        """Reverze migrace vrací původní placeholder kódy (nouzové vrácení)."""
        module = self._migration_module()
        part = self._make_practice("Revert 0,5", "uvazek_0_5")

        module.apply_employment_type_map(Practice, {v: k for k, v in module.LEGACY_TO_CANONICAL.items()})

        part.refresh_from_db()
        self.assertEqual(part.employment_type, LEGACY_PART_TIME)
