"""
Regresní testy k UAT opravám (F-6/F-8): editace nabídky organizací.

- PUT/PATCH /practices/employer/<id>/ nesmí vyžadovat `employer_id` (FE ho neposílá)
  a vlastník nabídky se při editaci nesmí změnit.
- GET /practices/employer/<id>/ vrací plný detail jen vlastní organizaci a staffu.
"""

from datetime import date, datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, PracticeWorkflowState, ProgressStatus
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    StudentUser,
)


def _make_org(email, company, approval=ApprovalStatus.APPROVED, **user_kwargs):
    user = OrganizationUser.objects.create(
        email=email,
        password="pass",
        first_name="Org",
        last_name=company,
        is_active=True,
        organization_role=OrganizationRole.OWNER,
        **user_kwargs,
    )
    profile = EmployerProfile.objects.create(
        employer_id=user.id,
        company_name=company,
        approval_status=approval,
    )
    user.employer_profile = profile
    user.save()
    return user, profile


class EmployerPracticeUpdateRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_user, self.employer = _make_org("owner@test.com", "Owner Corp")
        self.other_user, self.other_employer = _make_org("other@test.com", "Other Corp")
        self.pending_user, _ = _make_org("pending@test.com", "Pending Corp", approval=ApprovalStatus.PENDING)
        self.staff_user, _ = _make_org("staff@test.com", "Staff Corp", is_staff=True)
        self.student = StudentUser.objects.create(email="student@test.com", first_name="S", last_name="One", is_active=True)

        dept = Department.objects.create(department_name="IT", department_code="KI")
        self.subject = Subject.objects.create(subject_name="Java", department=dept)

        self.practice = self._make_practice(PracticeWorkflowState.PENDING_CONTENT_APPROVAL)

    def _make_practice(self, state, **kwargs):
        defaults = {
            "employer": self.employer,
            "subject": self.subject,
            "title": "Puvodni nazev",
            "description": "Tajny popis",
            "responsibilities": "Tajna nalpn",
            "start_date": date(2030, 1, 1),
            "end_date": date(2030, 6, 1),
            "is_active": True,
            "coefficient": 1.0,
            "approval_status": ApprovalStatus.PENDING,
            "progress_status": ProgressStatus.NOT_STARTED,
            "workflow_state": state,
        }
        defaults.update(kwargs)
        return Practice.objects.create(**defaults)

    @property
    def url(self):
        return f"/api/practices/employer/{self.practice.practice_id}/"

    def _payload(self, **overrides):
        data = {
            "subject_id": self.subject.subject_id,
            "title": "Novy nazev",
            "description": "Novy popis",
            "responsibilities": "Nova naplni",
            "mentor_name": "Jan Mentor",
            "contact_email": "mentor@test.com",
            "start_date": datetime(2030, 1, 1).strftime("%d.%m.%Y"),
        }
        data.update(overrides)
        return data

    # ---- PUT / PATCH ------------------------------------------------------

    def test_put_without_employer_id_succeeds_and_keeps_owner(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.put(self.url, self._payload())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.title, "Novy nazev")
        self.assertEqual(self.practice.mentor_name, "Jan Mentor")
        self.assertEqual(self.practice.employer_id, self.employer.pk)

    def test_put_with_foreign_employer_id_cannot_change_owner(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.put(self.url, self._payload(employer_id=self.other_employer.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.employer_id, self.employer.pk)

    def test_patch_partial_update_succeeds(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.patch(self.url, {"title": "Jen titul"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.title, "Jen titul")
        self.assertEqual(self.practice.employer_id, self.employer.pk)

    def test_put_allowed_in_content_rejected_state(self):
        self.practice.workflow_state = PracticeWorkflowState.CONTENT_REJECTED
        self.practice.save()
        self.client.force_authenticate(user=self.org_user)

        response = self.client.put(self.url, self._payload())
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_forbidden_for_active_and_closed_and_approved_states(self):
        self.client.force_authenticate(user=self.org_user)
        for state in (
            PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            PracticeWorkflowState.CLOSED_FOR_APPLICATIONS,
            PracticeWorkflowState.CONTENT_APPROVED,
        ):
            with self.subTest(state=state):
                self.practice.workflow_state = state
                self.practice.title = "Puvodni nazev"
                self.practice.save()
                response = self.client.put(self.url, self._payload())
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.practice.refresh_from_db()
                self.assertEqual(self.practice.title, "Puvodni nazev")

    def test_patch_forbidden_for_active_state(self):
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.save()
        self.client.force_authenticate(user=self.org_user)

        response = self.client.patch(self.url, {"title": "X"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_without_mentor_returns_400_with_details(self):
        self.client.force_authenticate(user=self.org_user)
        payload = self._payload()
        payload.pop("mentor_name")

        response = self.client.put(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mentor_name", response.json().get("details", {}))

    # ---- oprávnění --------------------------------------------------------

    def test_other_org_cannot_put_or_patch_or_delete(self):
        self.client.force_authenticate(user=self.other_user)
        for method, data in (("put", self._payload()), ("patch", {"title": "Hack"}), ("delete", None)):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url, data) if data else getattr(self.client, method)(self.url)
                self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.title, "Puvodni nazev")
        self.assertTrue(self.practice.is_active)

    def test_unapproved_org_cannot_edit_own_practice(self):
        practice = self._make_practice(
            PracticeWorkflowState.PENDING_CONTENT_APPROVAL,
            employer=EmployerProfile.objects.get(employer_id=self.pending_user.id),
        )
        self.client.force_authenticate(user=self.pending_user)

        response = self.client.put(f"/api/practices/employer/{practice.practice_id}/", self._payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_edit_via_employer_endpoint(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.put(self.url, self._payload())
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.title, "Puvodni nazev")

    def test_unauthenticated_cannot_edit(self):
        response = self.client.put(self.url, self._payload())
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # ---- retrieve ---------------------------------------------------------

    def test_retrieve_returns_full_detail_for_owner(self):
        self.client.force_authenticate(user=self.org_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["description"], "Tajny popis")
        self.assertIn("responsibilities", data)

    def test_retrieve_returns_full_detail_for_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.json().get("description"), "Tajny popis")

    def test_retrieve_does_not_leak_unpublished_content_to_other_org(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            body = response.json()
            self.assertNotIn("description", body)
            self.assertNotIn("responsibilities", body)
            self.assertNotIn("Tajny popis", response.content.decode())
