"""
Tests for Practice catalog listing and filtering.

Covers:
- Filter by subject + location (address)
- Filter by search (title/description)
- Filter by company_name
- Empty result
- Combination of multiple filters
- Authenticated access
"""

from datetime import date, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    StudentUser,
)


class CatalogFilterTests(TestCase):
    """Katalog praxí — filtrování a výpis."""

    def setUp(self):
        self.client = APIClient()

        # Student who browses the catalog
        self.student = StudentUser.objects.create(
            email="student@catalog.test",
            first_name="Test",
            last_name="Student",
            is_active=True,
        )

        # Employer for practices
        self.org_user = OrganizationUser.objects.create(
            email="org@catalog.test",
            password="pass",
            first_name="Org",
            last_name="User",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Katalog Corp",
            address="Praha, Václavské náměstí",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        # Second employer (for location-based filtering)
        self.org_user2 = OrganizationUser.objects.create(
            email="org2@catalog.test",
            password="pass",
            first_name="Org2",
            last_name="User",
            is_active=True,
        )
        self.employer2 = EmployerProfile.objects.create(
            employer_id=self.org_user2.id,
            company_name="Brno Corp",
            address="Brno, Moravské náměstí",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user2.employer_profile = self.employer2
        self.org_user2.save()

        # Subject / department
        self.dept = Department.objects.create(department_name="Informatika", department_code="KI")
        self.subject = Subject.objects.create(
            subject_name="Odborná praxe",
            subject_code="KI/BOP",
            department=self.dept,
            min_hours=480,
        )

        # Create practices
        today = date.today()
        self.practice_prague = Practice.objects.create(
            title="Vývojář v Praze",
            description="Python backend vývojář",
            employer=self.employer,
            subject=self.subject,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=100),
            available_positions=3,
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

        self.practice_brno = Practice.objects.create(
            title="Java vývojář v Brně",
            description="Java backend with Spring",
            employer=self.employer2,
            subject=self.subject,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=60),
            available_positions=0,
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

        self.practice_inactive = Practice.objects.create(
            title="Neaktivní praxe",
            description="Tato praxe již není aktivní",
            employer=self.employer,
            subject=self.subject,
            start_date=today,
            end_date=today + timedelta(days=30),
            is_active=False,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.CLOSED_FOR_APPLICATIONS,
        )

        self.catalog_url = "/api/practices/student/"

    def test_catalog_list_authenticated(self):
        """Authenticated student can list active practices."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        # Should include both active practices, not the inactive one
        titles = [r["title"] for r in results]
        self.assertIn("Vývojář v Praze", titles)
        self.assertIn("Java vývojář v Brně", titles)
        self.assertNotIn("Neaktivní praxe", titles)

    def test_filter_by_company_name(self):
        """Filter practices by employer company_name."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"company_name": "Brno"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")

    def test_filter_by_subject(self):
        """Filter practices by subject_id."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"subject": self.subject.subject_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

    def test_filter_by_address_location(self):
        """Filter practices by employer address (location)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"address": "Praha"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Vývojář v Praze")

    def test_filter_by_search_title(self):
        """Filter practices by search (title)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"search": "Java"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")

    def test_empty_result(self):
        """Filter with non-matching criteria returns empty result."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"company_name": "NonexistentXYZ"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    def test_combination_of_filters(self):
        """Combine subject + location filter."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(
            self.catalog_url,
            {"subject": self.subject.subject_id, "address": "Brno"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")

    # ------------------------------------------------------------------
    # Duration (min_duration / max_duration)
    # ------------------------------------------------------------------

    def test_filter_by_min_duration(self):
        """Filter practices by minimum duration (subject__min_hours >= value)."""
        self.client.force_authenticate(user=self.student)
        # Both practices have subject with min_hours=480
        # Use min_duration=400 → both should be returned
        response = self.client.get(self.catalog_url, {"min_duration": 400})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

        # Use min_duration=500 → no practices qualify
        response = self.client.get(self.catalog_url, {"min_duration": 500})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    def test_filter_by_max_duration(self):
        """Filter practices by maximum duration (subject__min_hours <= value)."""
        self.client.force_authenticate(user=self.student)
        # Both practices have subject with min_hours=480
        # Use max_duration=480 → both qualify
        response = self.client.get(self.catalog_url, {"max_duration": 480})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

        # Use max_duration=400 → no practices qualify
        response = self.client.get(self.catalog_url, {"max_duration": 400})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    def test_filter_by_min_and_max_duration(self):
        """Filter practices by both min and max duration simultaneously."""
        self.client.force_authenticate(user=self.student)
        # min_hours=480, so min_duration=400 AND max_duration=500 → should match
        response = self.client.get(
            self.catalog_url,
            {"min_duration": 400, "max_duration": 500},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

        # min_duration=400 AND max_duration=450 → should NOT match (480 > 450)
        response = self.client.get(
            self.catalog_url,
            {"min_duration": 400, "max_duration": 450},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    # ------------------------------------------------------------------
    # Capacity (has_capacity)
    # ------------------------------------------------------------------

    def test_filter_by_has_capacity_true(self):
        """Filter practices that still have free positions."""
        self.client.force_authenticate(user=self.student)
        # practice_prague: available_positions=3, approved_count=0 → has capacity
        # practice_brno: available_positions=0, approved_count=0 → NO capacity
        response = self.client.get(self.catalog_url, {"has_capacity": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Vývojář v Praze")

    def test_filter_by_has_capacity_false(self):
        """Filter practices that are full (no free positions)."""
        self.client.force_authenticate(user=self.student)
        # practice_brno: available_positions=0, approved_count=0 → full
        response = self.client.get(self.catalog_url, {"has_capacity": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")

    # ------------------------------------------------------------------
    # Skills (JSON field)
    # ------------------------------------------------------------------

    def test_filter_by_skills(self):
        """Filter practices by skills JSON field."""
        self.practice_prague.skills = ["Python", "Django", "PostgreSQL"]
        self.practice_prague.save()
        self.practice_brno.skills = ["Java", "Spring", "Hibernate"]
        self.practice_brno.save()

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"skills": "Python"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Vývojář v Praze")

        # Partial match (icontains on JSON string repr)
        response = self.client.get(self.catalog_url, {"skills": "Hiber"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")

        # No match
        response = self.client.get(self.catalog_url, {"skills": "NonexistentSkill"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def test_filter_by_favorites(self):
        """Filter practices by student's favorites."""
        self.student.favorite_practices.add(self.practice_prague)

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"favorites": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Vývojář v Praze")

        # favorites=false returns all (no filtering applied)
        response = self.client.get(self.catalog_url, {"favorites": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

    # ------------------------------------------------------------------
    # Active only
    # ------------------------------------------------------------------

    def test_filter_by_active_only(self):
        """Filter practices by is_active flag."""
        self.client.force_authenticate(user=self.student)

        # active_only=true → default: only is_active=True practices
        response = self.client.get(self.catalog_url, {"active_only": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

        # active_only=false → filtered on top of base queryset (is_active=True),
        # so no inactive practices surface
        response = self.client.get(self.catalog_url, {"active_only": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    # ------------------------------------------------------------------
    # Ordering / Date range
    # ------------------------------------------------------------------

    def test_filter_by_date_range(self):
        """Order practices by start_date/end_date."""
        self.client.force_authenticate(user=self.student)

        # Ascending by start_date
        response = self.client.get(self.catalog_url, {"ordering": "start_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)
        # practice_brno starts earlier (today+5) than practice_prague (today+10)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")
        self.assertEqual(results[1]["title"], "Vývojář v Praze")

        # Descending by start_date
        response = self.client.get(self.catalog_url, {"ordering": "-start_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(results[0]["title"], "Vývojář v Praze")
        self.assertEqual(results[1]["title"], "Java vývojář v Brně")

        # Descending by end_date
        response = self.client.get(self.catalog_url, {"ordering": "-end_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)

    # ------------------------------------------------------------------
    # Katalog: pouze schválené (OPEN_FOR_APPLICATIONS) + nestornované
    # ------------------------------------------------------------------

    def _create_catalog_practice(self, title, workflow_state, is_active=True, is_cancelled=False, **kwargs):
        today = date.today()
        return Practice.objects.create(
            title=title,
            description="popis",
            employer=self.employer,
            subject=self.subject,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=100),
            is_active=is_active,
            is_cancelled=is_cancelled,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=workflow_state,
            **kwargs,
        )

    def test_catalog_excludes_pending_content_approval(self):
        """PENDING_CONTENT_APPROVAL nabídka není v katalogu."""
        self._create_catalog_practice("Čeká na schválení obsahu", PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        titles = [r["title"] for r in results]
        self.assertNotIn("Čeká na schválení obsahu", titles)
        self.assertIn("Vývojář v Praze", titles)

    def test_catalog_excludes_content_rejected(self):
        """CONTENT_REJECTED nabídka není v katalogu."""
        self._create_catalog_practice("Zamítnutý obsah", PracticeWorkflowState.CONTENT_REJECTED)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        titles = [r["title"] for r in results]
        self.assertNotIn("Zamítnutý obsah", titles)

    def test_catalog_excludes_cancelled_practice(self):
        """stornovaná nabídka není v katalogu ani když je aktivní."""
        self._create_catalog_practice("Stornovaná stáž", PracticeWorkflowState.OPEN_FOR_APPLICATIONS, is_cancelled=True)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        titles = [r["title"] for r in results]
        self.assertNotIn("Stornovaná stáž", titles)

    def test_catalog_includes_open_for_applications(self):
        """OPEN_FOR_APPLICATIONS nabídka v katalogu je."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        titles = [r["title"] for r in results]
        self.assertIn("Vývojář v Praze", titles)
        self.assertIn("Java vývojář v Brně", titles)

    # ------------------------------------------------------------------
    # kraj (region) filtr + workflow_status_label + čítače
    # ------------------------------------------------------------------

    def test_filter_by_region(self):
        """filtr ?region=<kraj> (exact)."""
        self.practice_prague.region = "PHA"
        self.practice_prague.save(update_fields=["region"])
        self.practice_brno.region = "JHM"
        self.practice_brno.save(update_fields=["region"])

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url, {"region": "PHA"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Vývojář v Praze")

    def test_workflow_status_label_in_payload(self):
        """workflow_status_label pro OPEN_FOR_APPLICATIONS = „Aktivní"."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(results[0]["workflow_status_label"], "Aktivní")

    def test_approved_and_pending_applications_in_payload(self):
        """katalogový payload obsahuje approved_applications/pending_applications."""
        from student_practices.models import StudentPractice, StudentPracticeWorkflowState

        # UniqueConstraint(practice, user, is_cancelled=False) — proto dva různé právy.
        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice_prague,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.IN_PROGRESS,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        StudentPractice.objects.create(
            user=self.student,
            practice=self.practice_brno,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        prague = next(r for r in results if r["title"] == "Vývojář v Praze")
        brno = next(r for r in results if r["title"] == "Java vývojář v Brně")
        self.assertEqual(prague["approved_applications"], 1)
        self.assertEqual(prague["pending_applications"], 0)
        self.assertEqual(brno["approved_applications"], 0)
        self.assertEqual(brno["pending_applications"], 1)

    def test_mentor_contact_region_in_payload(self):
        """katalogový payload obsahuje mentor_name, contact_email, region."""
        self.practice_prague.mentor_name = "Ing. Petr Vedoucí"
        self.practice_prague.contact_email = "praxe@katalog.cz"
        self.practice_prague.region = "PHA"
        self.practice_prague.save(update_fields=["mentor_name", "contact_email", "region"])

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        prague = next(r for r in results if r["title"] == "Vývojář v Praze")
        self.assertEqual(prague["mentor_name"], "Ing. Petr Vedoucí")
        self.assertEqual(prague["contact_email"], "praxe@katalog.cz")
        self.assertEqual(prague["region"], "PHA")

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_pagination(self):
        """Test pagination with page_size and page parameters."""
        self.client.force_authenticate(user=self.student)

        # page_size=1 returns single result
        response = self.client.get(self.catalog_url, {"page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNotNone(response.data["next"])

        # page=2 with page_size=1 returns second result
        response = self.client.get(self.catalog_url, {"page_size": 1, "page": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # page beyond total returns 404 (DRF standard behavior)
        response = self.client.get(self.catalog_url, {"page_size": 1, "page": 99})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Default page_size (10) returns all 2 results
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def test_unauthenticated_access(self):
        """Unauthenticated users are rejected with 401."""
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_student_access(self):
        """Non-student (employer) can view the catalog (IsAuthenticated permission)."""
        self.client.force_authenticate(user=self.org_user)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        titles = [r["title"] for r in results]
        self.assertIn("Vývojář v Praze", titles)
        self.assertIn("Java vývojář v Brně", titles)

    # ------------------------------------------------------------------
    # Empty state
    # ------------------------------------------------------------------

    def test_catalog_empty_state(self):
        """When no practices exist, catalog returns empty results."""
        Practice.objects.all().delete()
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)
        self.assertEqual(response.data["count"], 0)

    # ------------------------------------------------------------------
    # Catalog ordering
    # ------------------------------------------------------------------

    def test_catalog_ordering(self):
        """Order practices by title and practice_id."""
        self.client.force_authenticate(user=self.student)

        # Ascending by title
        response = self.client.get(self.catalog_url, {"ordering": "title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Java vývojář v Brně")
        self.assertEqual(results[1]["title"], "Vývojář v Praze")

        # Descending by title
        response = self.client.get(self.catalog_url, {"ordering": "-title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(results[0]["title"], "Vývojář v Praze")
        self.assertEqual(results[1]["title"], "Java vývojář v Brně")

        # Ascending by practice_id (same as default creation order)
        response = self.client.get(self.catalog_url, {"ordering": "practice_id"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(results[0]["practice_id"], self.practice_prague.practice_id)
        self.assertEqual(results[1]["practice_id"], self.practice_brno.practice_id)
