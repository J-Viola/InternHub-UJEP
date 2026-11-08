"""
T5 – matice stavů: všech 14 stavů StudentPractice a 5 stavů Practice.

Ověřuje, že každý stav má lidsky čitelný popisek (ne „Neznámý“), že kartu vidí
vlastník a cizí student ne, a že se popisky stavů nabídky shodují s kanonickými
názvy (D-06).
"""

from datetime import date

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
    OrganizationUser,
    StudentUser,
)

SP_LABELS = {
    "APPLIED": "Čeká na schválení garanta",
    "PRELIMINARY_APPROVED": "Čeká na schválení organizací",
    "REJECTED": "Přihláška na praxi odmítnuta",
    "CONTRACTED": "Zasmluvněno",
    "STARTED": "Zahájeno",
    "ENDED": "Ukončeno",
    "COMPLETED": "Splněno",
    "AWAITING_CONTRACT": "Čeká na zasmluvnění",
    "AWAITING_DOCUMENTS": "Čeká na schválení dokumentů",
    "DOCUMENTS_REJECTED": "Dokumenty zamítnuty",
    "AWAITING_CONTENT_APPROVAL": "Čeká na schválení obsahu",
    "CONTENT_APPROVED": "Obsah praxe schválen",
    "CONTENT_REJECTED": "Zamítnutí obsahu",
    "DOCUMENTS_RESUBMITTED": "Opravené dokumenty čekají na kontrolu",
}

PRACTICE_LABELS = {
    "PENDING_CONTENT_APPROVAL": "Čeká na schválení obsahu",
    "CONTENT_APPROVED": "Čeká na aktivaci",
    "CONTENT_REJECTED": "Zamítnutí obsahu",
    "OPEN_FOR_APPLICATIONS": "Aktivní",
    "CLOSED_FOR_APPLICATIONS": "Uzavřeno",
}


class StateMatrixTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        dept = Department.objects.create(department_name="IT", department_code="KI")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=dept)
        self._n = 0
        self.foreign = StudentUser.objects.create(email="foreign@test.com", first_name="For", last_name="Eign", is_active=True)
        org = OrganizationUser.objects.create(email="org@test.com", is_active=True, organization_role=0)
        employer = EmployerProfile.objects.create(employer_id=org.id, company_name="Test Co", approval_status=ApprovalStatus.APPROVED)
        self.practice = Practice.objects.create(
            employer=employer,
            subject=self.subject,
            title="Praxe",
            description="Popis",
            responsibilities="Náplň",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 6, 1),
            is_active=True,
            coefficient=1.0,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
        )

    def _sp(self, state):
        # unikátní aktivní přihláška na uživatele → každý stav má vlastního studenta
        self._n += 1
        owner = StudentUser.objects.create(email=f"owner{self._n}@test.com", first_name="Own", last_name="Er", is_active=True)
        return StudentPractice.objects.create(
            user=owner,
            practice=self.practice,
            start_date=date(2027, 1, 1),
            end_date=date(2027, 6, 1),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
        )

    def test_every_student_practice_state_has_label_and_card_access(self):
        for state in StudentPracticeWorkflowState:
            with self.subTest(state=state.name):
                sp = self._sp(state)
                self.assertEqual(sp.workflow_status_label, SP_LABELS[state.name])

                self.client.force_authenticate(user=sp.user)
                own = self.client.get(f"/api/student-practices/{sp.student_practice_id}")
                self.assertEqual(own.status_code, status.HTTP_200_OK)

                self.client.force_authenticate(user=self.foreign)
                foreign = self.client.get(f"/api/student-practices/{sp.student_practice_id}")
                self.assertIn(foreign.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_every_practice_state_has_canonical_label(self):
        for state in PracticeWorkflowState:
            with self.subTest(state=state.name):
                self.practice.workflow_state = state
                self.practice.save(update_fields=["workflow_state"])
                self.practice.refresh_from_db()
                self.assertEqual(self.practice.workflow_status_label, PRACTICE_LABELS[state.name])
