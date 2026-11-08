"""
UAT TC-14-03: úprava zamítnutého inzerátu ho vrací do schvalovacího kolečka.

Po PUT/PATCH ve stavu CONTENT_REJECTED se inzerát přepne do PENDING_CONTENT_APPROVAL
a approval_status se resetuje na PENDING, aby ho garant znovu viděl a mohl schválit.
"""

from datetime import date

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
)


class OfferResubmitAfterRejectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_user = OrganizationUser.objects.create(
            email="owner@test.com",
            password="pass",
            first_name="Org",
            last_name="Owner",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Owner Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        dept = Department.objects.create(department_name="IT", department_code="KI")
        self.subject = Subject.objects.create(subject_name="Java", department=dept)

        self.practice = Practice.objects.create(
            employer=self.employer,
            subject=self.subject,
            title="Zamitnuty inzerat",
            description="Popis",
            responsibilities="Napln",
            start_date=date(2030, 1, 1),
            end_date=date(2030, 6, 1),
            is_active=True,
            coefficient=1.0,
            approval_status=ApprovalStatus.REJECTED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.CONTENT_REJECTED,
        )
        self.url = f"/api/practices/employer/{self.practice.practice_id}/"

    def _payload(self, **overrides):
        data = {
            "subject_id": self.subject.subject_id,
            "title": "Opraveny inzerat",
            "description": "Novy popis",
            "responsibilities": "Nova napln",
            "mentor_name": "Jan Mentor",
            "contact_email": "mentor@test.com",
            "start_date": "01.01.2030",
        }
        data.update(overrides)
        return data

    def test_put_returns_rejected_offer_to_pending_and_resets_approval(self):
        self.client.force_authenticate(user=self.org_user)

        response = self.client.put(self.url, self._payload())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        self.assertEqual(self.practice.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(self.practice.title, "Opraveny inzerat")

    def test_patch_returns_rejected_offer_to_pending(self):
        self.client.force_authenticate(user=self.org_user)

        response = self.client.patch(self.url, {"title": "Jen titul"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        self.assertEqual(self.practice.approval_status, ApprovalStatus.PENDING)

    def test_active_offer_is_still_not_editable(self):
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.approval_status = ApprovalStatus.APPROVED
        self.practice.save()
        self.client.force_authenticate(user=self.org_user)

        response = self.client.put(self.url, self._payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.practice.refresh_from_db()
        self.assertEqual(self.practice.workflow_state, PracticeWorkflowState.OPEN_FOR_APPLICATIONS)
