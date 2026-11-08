"""dokumentové přechody, hrana do ENDED, protokol PDF."""

import io
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from docx import Document
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentHelper,
    DocumentStatus,
    DocumentType,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
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
            # AWAITING_CONTRACT je dosažitelný jen po souhlasu školy i organizace (T1/C06-A).
            school_approved=True,
            employer_approved=True,
        )
        DocumentHelper.assign_default_documents(self.sp)
        self.sp.refresh_from_db()

    def _upload_contract(self):
        self.client.force_authenticate(user=self.student)
        url = f"/api/student-practices/upload-document/{self.sp.contract_document.document_id}"
        buf = io.BytesIO()
        Document().save(buf)
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
    """BL-06 oracle update (C19-B/T2c; expected regressions #6–#8).

    Korektní oracle opravné smyčky (T2c, reference:
    test_bl03_workflow.py::Bl03RepairLoopTests):
    - DOCUMENTS_REJECTED → ven vede JEN terminální REJECTED (admin + důvod);
      přímé DOCUMENTS_REJECTED → ENDED NEEXISTUJE;
    - oprava = OWNER upload → 201 + DOCUMENTS_RESUBMITTED (review-pending;
      upload ≠ approval) → review schválí (postup) nebo zamítne (zpět DR);
    - terminální REJECTED z opravného cyklu = výhradně admin + důvod.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.client = APIClient()
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
        # reviewer (garant) + admin pro terminální zamítnutí (T2c/R44)
        self.professor = ProfessorUser.objects.create_user(
            email="prof@m.test",
            password="password123",
            first_name="Karel",
            last_name="Prof",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.admin = get_user_model().objects.create_superuser(email="admin@m.test", password="password123")
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

    def _attach_doc(self, sp, *, doc_status=DocumentStatus.REJECTED):
        """Vytvoří zamítnutý dokument a připojí ho přes FK SP (manuálně,
        aby test nezávisel na defaultních šablonách)."""
        doc = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT, status=doc_status)
        sp.contract_document = doc
        sp.save(update_fields=["contract_document"])
        return doc

    def _upload(self, doc):
        self.client.force_authenticate(user=self.student)
        return self.client.post(
            f"/api/student-practices/upload-document/{doc.document_id}",
            {"document": SimpleUploadedFile("repaired.pdf", b"%PDF-1.4 wp10 repair", content_type="application/pdf")},
        )

    def _transition(self, actor, sp, target_state, reason="wp10 oracle"):
        return StudentPracticeService.transition_student_practice_state(sp, target_state, actor, reason=reason)

    def test_documents_rejected_to_ended_edge_standard(self):
        """T2c: přímá hrana DOCUMENTS_REJECTED → ENDED NEEXISTUJE (ani v standardním matrix);
        z DR vede jen terminální REJECTED; review-pending stav má vlastní hrany."""
        from student_practices.services import SP_TRANSITIONS

        self.assertNotIn(
            StudentPracticeWorkflowState.ENDED,
            SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED],
        )
        self.assertEqual(
            set(SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED]),
            {StudentPracticeWorkflowState.REJECTED},
        )
        self.assertEqual(
            set(SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED]),
            {
                StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
                StudentPracticeWorkflowState.ENDED,
                StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
                StudentPracticeWorkflowState.REJECTED,
            },
        )

    def test_documents_rejected_to_ended_edge_manual(self):
        """T2c: totéž v MANUAL_SP_TRANSITIONS (externí/manuální cyklus)."""
        from student_practices.services import MANUAL_SP_TRANSITIONS

        self.assertNotIn(
            StudentPracticeWorkflowState.ENDED,
            MANUAL_SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED],
        )
        self.assertEqual(
            set(MANUAL_SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_REJECTED]),
            {StudentPracticeWorkflowState.REJECTED},
        )
        self.assertEqual(
            set(MANUAL_SP_TRANSITIONS[StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED]),
            {
                StudentPracticeWorkflowState.AWAITING_DOCUMENTS,
                StudentPracticeWorkflowState.ENDED,
                StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
                StudentPracticeWorkflowState.REJECTED,
            },
        )

    def test_student_can_transition_documents_rejected_to_ended(self):
        """T2c: přímý studentův přechod DR → ENDED je zakázán; oprava vede
        přes owner upload → DOCUMENTS_RESUBMITTED → review rozhoduje."""
        from rest_framework.exceptions import PermissionDenied

        sp = self._sp(StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        doc = self._attach_doc(sp)

        # 1) negativní: student DR → ENDED přímo → ValueError, stav beze změny
        with self.assertRaises(ValueError):
            self._transition(self.student, sp, StudentPracticeWorkflowState.ENDED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)

        # 2) kolo 1: owner upload → 201 + review-pending (upload ≠ approval)
        response = self._upload(doc)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sp.refresh_from_db()
        doc.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.assertEqual(doc.status, DocumentStatus.PENDING)

        # 3) předčasný postup bez review opraveného dokladu → 400, stav beze změny
        with self.assertRaises(ValueError):
            self._transition(self.professor, sp, StudentPracticeWorkflowState.ENDED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)

        # 4) Rejection is recorded by document review, not by a generic state transition.
        self.client.force_authenticate(user=self.professor)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{doc.document_id}",
            {"status": DocumentStatus.REJECTED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        sp.refresh_from_db()
        doc.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self.assertEqual(doc.status, DocumentStatus.REJECTED)

        # 5) kolo 2: owner upload → DOCUMENTS_RESUBMITTED; review SCHVÁLÍ doklad → postup
        self.assertEqual(self._upload(doc).status_code, status.HTTP_201_CREATED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_RESUBMITTED)
        self.client.force_authenticate(user=self.professor)
        reviewed = self.client.patch(
            f"/api/student-practices/review-document/{doc.document_id}",
            {"status": DocumentStatus.APPROVED.value},
            format="json",
        )
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        # Brána do ENDED vyžaduje schválenou závěrečnou dokumentaci; tento scénář
        # opravuje smlouvu, takže závěrečný doklad doplníme až před přechodem.
        feedback = UploadedDocument.objects.create(document_type=DocumentType.FEEDBACK, status=DocumentStatus.APPROVED)
        sp.feedback_document = feedback
        sp.save(update_fields=["feedback_document"])
        self._transition(self.professor, sp, StudentPracticeWorkflowState.ENDED)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, StudentPracticeWorkflowState.ENDED)

        # 6) terminální REJECTED z opravného cyklu = výhradně admin + důvod (T2c/R44)
        other_student = StudentUser.objects.create(email="student2@m.test", first_name="Petr", last_name="Druhý", is_active=True)
        sp2 = StudentPractice.objects.create(
            user=other_student,
            practice=self.practice,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
        )
        self._attach_doc(sp2)
        with self.assertRaises(PermissionDenied):
            self._transition(self.professor, sp2, StudentPracticeWorkflowState.REJECTED)
        sp2.refresh_from_db()
        self.assertEqual(sp2.workflow_state, StudentPracticeWorkflowState.DOCUMENTS_REJECTED)
        self._transition(self.admin, sp2, StudentPracticeWorkflowState.REJECTED, reason="T2c terminální důvod")
        sp2.refresh_from_db()
        self.assertEqual(sp2.workflow_state, StudentPracticeWorkflowState.REJECTED)


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
        # „Splněno": ě je glyf (\\006), zbytek může být v jednom i ve dvou font runech (dle verze ReportLab)
        self.assertRegex(stream, r"Spln\\\d{3}(?:\)[^(]*\()?no\)")
        self.assertIn("Potvrzen", stream)
        self.assertIn("et hodin", stream)

    def test_completion_protocol_not_fully_completed_says_nesplneno(self):
        """Nedokončená praxe → výsledné hodnocení „Nesplněno"."""
        self.sp.workflow_state = StudentPracticeWorkflowState.ENDED
        pdf_bytes = PDFCompletionProtocolGenerator.generate_pdf(self.sp)
        stream = self._pdf_streams(pdf_bytes)
        self.assertRegex(stream, r"Nespln\\\d{3}(?:\)[^(]*\()?no\)")
