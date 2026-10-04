"""dokumentové přechody, hrana do ENDED, protokol PDF."""

import io
import zipfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    StudentPractice,
    StudentPracticeWorkflowState,
)
from student_practices.pdf_service import PDFCompletionProtocolGenerator
from student_practices.services import StudentPracticeService
from subject.models import Subject
from users.constants import ActionLogType
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class DocumentTransitionTests(TestCase):
    """upload mění stav, review schválení → CONTRACTED, zamítnutí → DOCUMENTS_REJECTED."""

    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)

        self.student = StudentUser.objects.create(email="student@doc.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(
            email="org@doc.test",
            is_active=True,
            organization_role=OrganizationRole.OWNER,
        )
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Doc Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()

        self.professor = ProfessorUser.objects.create_user(
            email="prof@doc.test",
            password="password123",
            first_name="Karel",
            last_name="Prof",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )

        self.practice = Practice.objects.create(
            title="Doc praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=5,
        )

        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT,
        )
        DocumentHelper.assign_default_documents(self.sp)
        self.sp.refresh_from_db()

    def _upload_contract(self):
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.sp.contract_document.document_id}"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
        buf.seek(0)
        file = SimpleUploadedFile(
            "contract.docx",
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        return self.client.post(url, {"document": file}, format="multipart")

    def test_upload_contract_changes_state_to_awaiting_documents(self):
        """Nahrání smluvního dokumentu z AWAITING_CONTRACT → AWAITING_DOCUMENTS + ActionLog."""
        response = self._upload_contract()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)

        logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=self.sp.student_practice_id,
            action_type=ActionLogType.STATE_TRANSITION,
        )
        self.assertTrue(logs.exists())
        self.assertIn("AWAITING_DOCUMENTS", logs.last().action_description)

    def test_review_approve_contract_leads_to_contracted(self):
        """Schválení smluvního dokumentu → CONTRACTED (NE STARTED)."""
        self._upload_contract()
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.AWAITING_DOCUMENTS)

        self.client.force_authenticate(user=self.professor)
        url = f"/api/student-practices/review-document/{self.sp.contract_document.document_id}"
        response = self.client.patch(url, {"status": DocumentStatus.APPROVED.value, "review_note": "OK"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.CONTRACTED)
        self.assertNotEqual(self.sp.workflow_state, StudentPracticeWorkflowState.STARTED)
        self.assertEqual(self.sp.progress_status, ProgressStatus.NOT_STARTED)

    def test_review_reject_contract_leads_to_documents_rejected(self):
        """Zamítnutí smluvního dokumentu → DOCUMENTS_REJECTED s rejection_reason."""
        self._upload_contract()
        self.sp.refresh_from_db()

        self.client.force_authenticate(user=self.professor)
        url = f"/api/student-practices/review-document/{self.sp.contract_document.document_id}"
        response = self.client.patch(
            url,
            {"status": DocumentStatus.REJECTED.value, "review_note": "Chybějící podpis smlouvy"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.sp.refresh_from_db()
        self.assertEqual(self.sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(self.sp.rejection_reason, "Chybějící podpis smlouvy")


class ManualCycleEdgeTests(TestCase):
    """hrana DOCUMENTS_REJECTED → ENDED."""

    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(email="student@m.test", first_name="Jan", last_name="Novák", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="org@m.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="M Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.practice = Practice.objects.create(
            title="Manuální praxe",
            employer=self.employer,
            subject=self.subject,
            is_external=True,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )

    def _sp(self, state):
        return StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
        )

    def test_documents_rejected_to_ended_edge_standard(self):
        """Hrana DOCUMENTS_REJECTED → ENDED existuje v SP_TRANSITIONS."""
        from student_practices.services import SP_TRANSITIONS

        self.assertIn(
            StudentPracticeWorkflowState.ENDED,
            SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED],
        )

    def test_documents_rejected_to_ended_edge_manual(self):
        """Hrana DOCUMENTS_REJECTED → ENDED existuje i v MANUAL_SP_TRANSITIONS."""
        from student_practices.services import MANUAL_SP_TRANSITIONS

        self.assertIn(
            StudentPracticeWorkflowState.ENDED,
            MANUAL_SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED],
        )

    def test_student_can_transition_documents_rejected_to_ended(self):
        """Student smí přejít DOCUMENTS_REJECTED → ENDED."""
        sp = self._sp(StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        sp = StudentPracticeService.transition_student_practice_state(
            sp,
            StudentPracticeWorkflowState.ENDED,
            self.student,
            reason="Nahrání opravených závěrečných dokumentů",
        )
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)


class CompletionProtocolPdfTests(TestCase):
    """Protokol o absolvování odborné praxe obsahuje povinné údaje."""

    @staticmethod
    def _pdf_streams(pdf_bytes):
        """Rozbalí ASCII85+FlateDecode streamy reportlab PDF (raw text operátorů)."""
        import base64
        import re
        import zlib

        raw = pdf_bytes.decode("latin-1", errors="ignore")
        parts = []
        for stream in re.findall(r"stream\r?\n(.*?)(?:\r?\n)?endstream", raw, re.S):
            try:
                a85_data = stream.split("~>")[0]
                inflated = zlib.decompress(base64.a85decode(a85_data))
                parts.append(inflated.decode("latin-1", errors="ignore"))
            except Exception:
                continue
        return "\n".join(parts)

    def setUp(self):
        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)
        self.student = StudentUser.objects.create(
            email="student@pdf.test",
            first_name="Jan",
            last_name="Novák",
            os_cislo="A12345",
            field_of_study="Informatika",
            is_active=True,
        )
        self.org_user = OrganizationUser.objects.create(email="org@pdf.test", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Pdf Corp",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.practice = Practice.objects.create(
            title="Pdf praxe",
            employer=self.employer,
            subject=self.subject,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        self.sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.COMPLETED,
            workflow_state=StudentPracticeWorkflowState.COMPLETED,
            hours_completed=480,
        )

    def test_completion_protocol_contains_required_data(self):
        """PDF obsahuje jméno, os. číslo, obor, firmu, hodiny a výsledné hodnocení.

        Diakritika (ě/č/ř) je v TrueType streamu zapsaná jako osmičkový glyf
        (např. „Spln\\006no" = „Splněno") — ověřujeme přes regulární výraz,
        ASCII části přímo.
        """
        pdf_bytes = PDFCompletionProtocolGenerator.generate_pdf(self.sp)
        self.assertGreater(len(pdf_bytes), 1000)
        stream = self._pdf_streams(pdf_bytes)

        self.assertIn("PROTOKOL O ABSOLVOV", stream)
        self.assertIn("Jan Nov", stream)  # „Jan Novák" (á jako glyf)
        self.assertIn("A12345", stream)
        self.assertIn("Informatika", stream)
        self.assertIn("Pdf Corp", stream)
        self.assertIn("480", stream)
        self.assertRegex(stream, r"Spln\\[0-7]{1,3}no")  # „Splněno"
        self.assertRegex(stream, r"Potvrzen\\[0-7]{1,3} po\\[0-7]{1,3}et")  # „Potvrzený počet"

    def test_completion_protocol_not_fully_completed_says_nesplneno(self):
        """Nedokončená praxe → výsledné hodnocení „Nesplněno"."""
        self.sp.workflow_state = StudentPracticeWorkflowState.ENDED
        pdf_bytes = PDFCompletionProtocolGenerator.generate_pdf(self.sp)
        stream = self._pdf_streams(pdf_bytes)
        self.assertRegex(stream, r"Nespln\\[0-7]{1,3}no")
