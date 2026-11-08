from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from test_support.contracts import approve_contract_document

from department.models import Department
from practices.models import Practice, PracticeWorkflowState
from student_practices.models import (
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
)
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
        # F-13: dashboard je agenda garanta/admina; student nesmí vidět globální data.
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/dashboard/stats/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

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
        self.assertIn("ID přihlášky", csv_content)

    def _attach_subject_and_mentor(self):
        """BL-06 fixture: předmět + garant předmětu (mentor) pro scope hodnotitele."""
        department = Department.objects.create(department_name="P2 KI", department_code="CKI")
        subject = Subject.objects.create(subject_name="P2 praxe", subject_code="CP2/BOP", department=department)
        self.practice.subject = subject
        self.practice.save(update_fields=["subject"])
        mentor = ProfessorUser.objects.create_user(
            email="mentor_p2@example.com",
            password="Password123!",
            first_name="Mentor",
            last_name="P2",
            is_active=True,
            department=department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        subject.subject_manager_id = mentor.pk
        subject.save(update_fields=["subject_manager"])
        return mentor

    def test_evaluation_submission(self):
        """BL-06 oracle update (MAJOR-1 / BE-002, bl01-decisions expected regression #1).

        Korektní oracle: mentor (hodnotitel v scope přihlášky) evaluaci ZALOŽÍ
        (201 + řádek s evaluated_by=mentor); STUDENT ji zakládat nesmí
        (403 + žádný řádek) — hodnotitelem je mentor, ne student.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        mentor = self._attach_subject_and_mentor()

        def pdf():
            return SimpleUploadedFile("test.pdf", b"%PDF-1.4 test content", content_type="application/pdf")

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

        # 1) Student: zápis evaluace je zakázán (403) a řádek NEVZNIKNE
        self.client.force_authenticate(user=self.student)
        res = self.client.post("/api/student-practices/evaluations/", {**payload, "pdf_file": pdf()})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Evaluation.objects.filter(student_practice=self.sp).exists())

        # 2) Mentor: 201 + řádek evidující hodnotitele
        self.client.force_authenticate(user=mentor)
        res = self.client.post("/api/student-practices/evaluations/", {**payload, "pdf_file": pdf()})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        evaluation = Evaluation.objects.get(student_practice=self.sp)
        self.assertEqual(evaluation.evaluated_by_id, mentor.pk)

    def test_confirm_contract_endpoint(self):
        """BL-06 oracle update (T1/C06-A + T2b; bl01-decisions expected regression #2).

        Korektní oracle:
        - owner-student potvrzuje POUZE přijetí (receipt): 200, stav ani osy se
          nemění, zapíše se contract_received_date; opakování = idempentní no-op;
        - CONTRACTED vzniká JEN po obou nezávislých osách (org → employer osa,
          škola → school osa) — dvou-role sekvence;
        - potvrzení z nepředkontrakčního stavu → 400 bez mutace (T2b).
        """
        from notifications.models import Notification

        mentor = self._attach_subject_and_mentor()
        org_user = OrganizationUser.objects.create(email="org_p2@example.com", is_active=True, organization_role=OrganizationRole.OWNER)
        org_user.employer_profile = self.employer
        org_user.save()
        # in-app ALLOCATION_ORG jde na practice.contact_user
        self.practice.contact_user = org_user
        self.practice.save(update_fields=["contact_user"])

        confirm_url = f"/api/student-practices/{self.sp.student_practice_id}/confirm-contract/"

        # fixture: předkontrakční stav (T2b povolený zdrojový stav)
        self.sp.workflow_state = StudentPracticeWorkflowState.AWAITING_CONTRACT
        self.sp.save(update_fields=["workflow_state"])

        # 1) owner-student: receipt-only — 200, stav i obě osy beze změny
        self.client.force_authenticate(user=self.student)
        res = self.client.post(confirm_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        self.assertFalse(self.sp.school_approved)
        self.assertFalse(self.sp.employer_approved)
        self.assertIsNotNone(self.sp.contract_received_date)

        # 1b) opakování stejné osy = idempentní 200 no-op (T2b), datum se nepřepisuje
        receipt_date = self.sp.contract_received_date
        res = self.client.post(confirm_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.contract_received_date, receipt_date)
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)

        # 2) org osa (employer) — stále jen jedna osa → stav zůstává
        self.client.force_authenticate(user=org_user)
        res = self.client.post(confirm_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertTrue(self.sp.employer_approved)
        self.assertFalse(self.sp.school_approved)
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.AWAITING_CONTRACT)
        # pending akce nealokuje — žádná ALLOCATION notifikace (T1)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=org_user).count(), 0)

        # 3) druhá osa (škola) → CONTRACTED + APPROVED + přesně jedna allokační notifikace
        approve_contract_document(self.sp)  # A-11: smlouva musí být schválená
        self.client.force_authenticate(user=mentor)
        res = self.client.post(confirm_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertEqual(self.sp.approval_status, ApprovalStatus.APPROVED)
        self.assertTrue(self.sp.school_approved)
        self.assertTrue(self.sp.employer_approved)
        self.assertEqual(Notification.objects.filter(verb="ALLOCATION_ORG", recipient=org_user).count(), 1)

        # 4) T2b: potvrzení z NEpředkontrakčního stavu → 400 bez mutace
        self.sp.workflow_state = StudentPracticeWorkflowState.ENDED
        self.sp.contract_received_date = None
        self.sp.school_approved = False
        self.sp.employer_approved = False
        self.sp.save(update_fields=["workflow_state", "contract_received_date", "school_approved", "employer_approved"])
        self.client.force_authenticate(user=self.student)
        res = self.client.post(confirm_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.ENDED)
        self.assertIsNone(self.sp.contract_received_date)
