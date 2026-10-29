"""Regresní testy oprav z nezávislého review (26. 10. 2026).

Pokrývá: firemní osa při schválení organizací, pořadí bran A-11 (osa → dokument → kapacita),
approval_status po vstupu do CONTRACTED, zámek stavových polí v adminu, throttling interních
endpointů, oprávnění k souborům (None == None, deaktivované vazby, garant), PDF signaturu CV
a publikaci cache SystemSettings až po commitu.
"""

import io

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from test_support.contracts import approve_contract_document

from api.file_access import StorageAccess, check_storage_access
from api.models import SystemSettings
from api.views import HealthCheckView, StorageAuthCheckView
from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    ApprovalStatus,
    DocumentType,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from student_practices.services import (
    AxesIncompleteError,
    ContractDocumentNotApprovedError,
    StudentPracticeService,
)
from student_practices.tests.test_bl03_workflow import BL03FixtureMixin
from subject.models import Subject
from users.models import (
    ActionLog,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    UserSubject,
    UserSubjectType,
)

ST = StudentPracticeWorkflowState


class EmployerAxisOnApprovalTests(BL03FixtureMixin, TestCase):
    def test_organization_approval_records_only_employer_axis(self):
        sp = self.make_sp(self.owner_student, state=ST.PRELIMINARY_APPROVED)
        StudentPracticeService.transition_student_practice_state(sp, ST.AWAITING_CONTRACT, self.org_user)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, ST.AWAITING_CONTRACT)
        self.assertTrue(sp.employer_approved)
        self.assertFalse(sp.school_approved)


class GateOrderTests(BL03FixtureMixin, TestCase):
    def _full_practice(self):
        practice = self.make_practice(title="Review plná", available_positions=1)
        other = self.make_sp(self.other_student, practice=practice, state=ST.CONTRACTED)
        StudentPractice.objects.filter(pk=other.pk).update(school_approved=True, employer_approved=True)
        return practice

    def test_missing_axis_beats_full_capacity(self):
        sp = self.make_sp(
            self.owner_student,
            practice=self._full_practice(),
            state=ST.AWAITING_CONTRACT,
        )
        with self.assertRaises(AxesIncompleteError):
            StudentPracticeService.transition_student_practice_state(sp, ST.CONTRACTED, self.garant)

    def test_unapproved_contract_beats_full_capacity(self):
        sp = self.make_sp(
            self.owner_student,
            practice=self._full_practice(),
            state=ST.AWAITING_CONTRACT,
        )
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True, employer_approved=True)
        sp.refresh_from_db()
        with self.assertRaises(ContractDocumentNotApprovedError):
            StudentPracticeService.transition_student_practice_state(sp, ST.CONTRACTED, self.garant)

    def test_confirm_contract_reports_axes_before_capacity(self):
        sp = self.make_sp(
            self.owner_student,
            practice=self._full_practice(),
            state=ST.AWAITING_CONTRACT,
        )
        self.client.force_authenticate(user=self.org_user)
        response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/confirm-contract/")
        self.assertEqual(response.status_code, 200, response.data)  # osa zapsána, bez CAPACITY_FULL
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, ST.AWAITING_CONTRACT)

    def test_entry_via_awaiting_documents_sets_approved_status(self):
        sp = self.make_sp(self.owner_student, state=ST.AWAITING_DOCUMENTS)
        StudentPractice.objects.filter(pk=sp.pk).update(school_approved=True, employer_approved=True)
        sp.refresh_from_db()
        approve_contract_document(sp)
        StudentPracticeService.transition_student_practice_state(sp, ST.CONTRACTED, self.garant)
        sp.refresh_from_db()
        self.assertEqual(sp.workflow_state, ST.CONTRACTED)
        self.assertEqual(sp.approval_status, ApprovalStatus.APPROVED)


class AdminLockTests(TestCase):
    def test_state_fields_are_readonly(self):
        model_admin = admin.site._registry[StudentPractice]
        for field in (
            "workflow_state",
            "school_approved",
            "employer_approved",
            "approval_status",
            "progress_status",
        ):
            with self.subTest(field=field):
                self.assertIn(field, model_admin.readonly_fields)


class InternalEndpointsNotThrottledTests(TestCase):
    def test_health_and_auth_gate_have_no_throttling(self):
        self.assertEqual(HealthCheckView().get_throttles(), [])
        self.assertEqual(StorageAuthCheckView().get_throttles(), [])


class FileAccessReviewTests(BL03FixtureMixin, TestCase):
    def _external_doc(self):
        practice = self.make_practice(title="Review externí", external=True)
        sp = self.make_sp(self.owner_student, practice=practice, state=ST.AWAITING_DOCUMENTS)
        doc = UploadedDocument.objects.create(document_type=DocumentType.CONTRACT)
        doc.document.name = "documents/review_external.docx"
        doc.save()
        sp.contract_document = doc
        sp.save(update_fields=["contract_document"])
        return doc

    def test_org_without_company_cannot_open_external_practice_document(self):
        self._external_doc()
        orphan = OrganizationUser.objects.create(email="orphan@review.test", is_active=True)
        self.assertIsNone(orphan.employer_profile_id)
        self.assertIs(
            check_storage_access(orphan, "documents/review_external.docx"),
            StorageAccess.DENIED,
        )

    def _cv_setup(self):
        self.owner_student.cv_file.name = "storage/documents/cvs/review_cv.pdf"
        self.owner_student.save()
        teacher = ProfessorUser.objects.create_user(
            email="teacher@review.test",
            password="x-review-pw",
            is_active=True,
            department=self.other_department,
        )
        link_student = UserSubject.objects.create(user=self.owner_student, subject=self.subject, role=UserSubjectType.Student)
        link_teacher = UserSubject.objects.create(user=teacher, subject=self.subject, role=UserSubjectType.Professor)
        return teacher, link_student, link_teacher

    def test_deactivated_links_revoke_private_file_access(self):
        teacher, link_student, link_teacher = self._cv_setup()
        path = "documents/cvs/review_cv.pdf"
        self.assertIs(check_storage_access(teacher, path), StorageAccess.ALLOWED)
        UserSubject.objects.filter(pk=link_teacher.pk).update(is_active=False)
        self.assertIs(check_storage_access(teacher, path), StorageAccess.DENIED)
        UserSubject.objects.filter(pk=link_teacher.pk).update(is_active=True)
        UserSubject.objects.filter(pk=link_student.pk).update(is_active=False)
        self.assertIs(check_storage_access(teacher, path), StorageAccess.DENIED)

    def test_garant_without_head_role_sees_own_department_only(self):
        garant_only = ProfessorUser.objects.create_user(
            email="garant-only@review.test",
            password="x-review-pw",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.TEACHER,
            is_garant_praxe=True,
        )
        foreign_garant = ProfessorUser.objects.create_user(
            email="garant-foreign@review.test",
            password="x-review-pw",
            is_active=True,
            department=self.other_department,
            department_role=DepartmentRole.TEACHER,
            is_garant_praxe=True,
        )
        self._cv_setup()
        doc = self._external_doc()
        doc_path = doc.document.name
        self.assertIs(check_storage_access(garant_only, doc_path), StorageAccess.ALLOWED)
        self.assertIs(check_storage_access(foreign_garant, doc_path), StorageAccess.DENIED)
        self.assertIs(
            check_storage_access(garant_only, "documents/cvs/review_cv.pdf"),
            StorageAccess.ALLOWED,
        )
        self.assertIs(
            check_storage_access(foreign_garant, "documents/cvs/review_cv.pdf"),
            StorageAccess.DENIED,
        )

    def test_colliding_names_require_access_to_every_owner(self):
        """Jméno s `storage/` prefixem i bez patří dvěma studentům → povoleno jen tomu, kdo smí vidět oba."""
        self.owner_student.cv_file.name = "storage/documents/cvs/collide.pdf"
        self.owner_student.save()
        self.other_student.cv_file.name = "documents/cvs/collide.pdf"
        self.other_student.save()
        path = "documents/cvs/collide.pdf"
        self.assertIs(check_storage_access(self.owner_student, path), StorageAccess.DENIED)
        self.assertIs(check_storage_access(self.other_student, path), StorageAccess.DENIED)
        self.assertIs(check_storage_access(self.admin, path), StorageAccess.ALLOWED)


class CvPdfSignatureTests(BL03FixtureMixin, TestCase):
    def _put(self, name, content):
        self.client.force_authenticate(user=self.owner_student)
        return self.client.patch(
            "/api/users/profile/",
            {"cv_file": SimpleUploadedFile(name, content, content_type="application/pdf")},
            format="multipart",
        )

    def test_fake_pdf_rejected_real_pdf_accepted(self):
        fake = self._put("fake.pdf", b"<html>not a pdf</html>")
        self.assertEqual(fake.status_code, 400, getattr(fake, "data", None))
        self.assertIn("cv_file", fake.data["details"])
        ok = self._put("real.pdf", b"%PDF-1.4 review")
        self.assertEqual(ok.status_code, 200, getattr(ok, "data", None))


class SystemSettingsCacheOnCommitTests(TransactionTestCase):
    def test_rollback_does_not_publish_cache(self):
        cache.clear()
        SystemSettings.get_solo()  # naplní cache výchozími hodnotami
        original = SystemSettings.get_solo().practice_contract_overdue_days
        try:
            with transaction.atomic():
                obj = SystemSettings.get_solo()
                obj.practice_contract_overdue_days = original + 3
                obj.save()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        self.assertEqual(SystemSettings.get_solo().practice_contract_overdue_days, original)

    def test_commit_publishes_cache(self):
        obj = SystemSettings.get_solo()
        obj.practice_contract_overdue_days = 11
        obj.save()
        self.assertEqual(SystemSettings.get_solo().practice_contract_overdue_days, 11)


class StorageApiHidesExistenceTests(BL03FixtureMixin, TestCase):
    """A-20: nepovolený přístup k souboru je pro přihlášeného nerozlišitelný od neexistujícího (404)."""

    def setUp(self):
        super().setUp()
        sp = self.make_sp(self.owner_student, state=ST.AWAITING_DOCUMENTS)
        self.doc = self.make_doc(sp, doc_type=DocumentType.CONTRACT)
        self.doc.document.name = "documents/a20_contract.docx"
        self.doc.save(update_fields=["document"])

    def _get(self, user, rel):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get(f"/api/files/{rel}/")

    def test_denied_and_missing_look_the_same(self):
        denied = self._get(self.other_student, "documents/a20_contract.docx")
        missing = self._get(self.other_student, "documents/a20_neexistuje.docx")
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(missing.status_code, 404)

    def test_unauthenticated_still_401(self):
        self.assertEqual(APIClient().get("/api/files/documents/a20_contract.docx/").status_code, 401)


class CancellationRequestBlocksAnyApplicationTests(BL03FixtureMixin, TestCase):
    """BDD UC05 AC-04 a AC-05."""

    APPLY_URL = "/api/practices/student/apply/"

    def _request_cancellation(self):
        sp = self.make_sp(self.owner_student, state=ST.CONTRACTED)
        StudentPracticeService.submit_cancellation_request(sp, self.owner_student, "Zdravotní důvody")
        return sp

    def test_pending_request_blocks_application_for_other_subject(self):
        self._request_cancellation()
        self.client.force_authenticate(user=self.owner_student)
        response = self.client.post(self.APPLY_URL, {"practice": self.practice_other_subject.practice_id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(response.data))

    def test_other_student_is_not_blocked(self):
        self._request_cancellation()
        self.client.force_authenticate(user=self.other_student)
        response = self.client.post(self.APPLY_URL, {"practice": self.practice_other_subject.practice_id}, format="json")
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))

    def test_audit_log_records_date_and_reason(self):
        sp = self._request_cancellation()
        log = ActionLog.objects.filter(object_type="StudentPractice", object_id=sp.student_practice_id).latest("pk")
        self.assertIn("Zdravotní důvody", log.action_description)
        self.assertIn(timezone.now().date().isoformat(), log.action_description)


class SeedDemoCollisionTests(TestCase):
    """A-18: seed odmítne převzít cizí data a nic nezapíše."""

    def _seed(self):
        out = io.StringIO()
        call_command("seed_demo", "--password", "a18-test-pw", stdout=out)
        return out.getvalue()

    def test_foreign_subject_with_demo_code_is_rejected(self):
        dep = Department.objects.create(department_name="Cizí katedra", department_code="CIZI")
        other_manager = ProfessorUser.objects.create_user(
            email="cizi.spravce@a18.test", password="a18-only-password", department=dep, department_role=DepartmentRole.HEAD
        )
        Subject.objects.create(subject_name="Cizí předmět", subject_code="DEMO-PRAXE", department=dep, subject_manager=other_manager)
        with self.assertRaisesMessage(CommandError, "DEMO-PRAXE"):
            self._seed()
        self.assertEqual(Subject.objects.get(subject_code="DEMO-PRAXE").subject_manager_id, other_manager.pk)
        self.assertFalse(get_user_model().objects.filter(email="demo.org@test.local").exists())

    def test_foreign_practice_title_is_rejected(self):
        dep = Department.objects.create(department_name="Cizí katedra", department_code="CIZI")
        subject = Subject.objects.create(subject_name="Cizí předmět", subject_code="CIZI/BOP", department=dep)
        foreign = EmployerProfile.objects.create(company_name="Cizí firma", approval_status=ApprovalStatus.APPROVED)
        Practice.objects.create(
            title="DEMO Standard",
            employer=foreign,
            subject=subject,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        with self.assertRaisesMessage(CommandError, "DEMO Standard"):
            self._seed()
        self.assertFalse(get_user_model().objects.filter(email="demo.org@test.local").exists())

    def test_foreign_profile_with_colliding_pk_is_not_adopted(self):
        # profil s PK, který by dřív převzal ``employer_id=user.pk``
        next_pk = (OrganizationUser.objects.order_by("-pk").values_list("pk", flat=True).first() or 0) + 1
        foreign = EmployerProfile.objects.create(employer_id=next_pk, company_name="Cizí firma", approval_status=ApprovalStatus.APPROVED)
        self._seed()
        org_user = OrganizationUser.objects.get(email="demo.org@test.local")
        self.assertNotEqual(org_user.employer_profile_id, foreign.pk)
        foreign.refresh_from_db()
        self.assertEqual(foreign.company_name, "Cizí firma")
        self.assertTrue(org_user.employer_profile.company_name.startswith("SYNTHETIC DEMO DATA"))

    def test_rerun_is_idempotent(self):
        self._seed()
        before = (EmployerProfile.objects.count(), Practice.objects.count(), Subject.objects.count())
        self._seed()
        self.assertEqual(before, (EmployerProfile.objects.count(), Practice.objects.count(), Subject.objects.count()))
