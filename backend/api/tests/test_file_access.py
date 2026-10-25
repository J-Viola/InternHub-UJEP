"""A-01 / A-25 — autorizace souborů v ``/storage/`` (auth_request, API view, middleware).

Všichni tři strážci rozhodují stejnou funkcí ``check_storage_access``; test
ověřuje matici role × typ souboru × vlastník a bezpečnost cest (traversal).
"""

from django.test import TestCase
from rest_framework.test import APIClient

from api.file_access import (
    StorageAccess,
    canonical_rel_path,
    check_storage_access,
    rel_path_from_uri,
)
from student_practices.models import DocumentType, StudentPracticeWorkflowState
from student_practices.tests.test_bl03_workflow import BL03FixtureMixin
from users.models import UserSubject, UserSubjectType

CHECK_URL = "/api/auth/check/"


class StorageAccessMatrixTests(BL03FixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        sp = self.make_sp(self.owner_student, state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS)
        self.doc = self.make_doc(sp, doc_type=DocumentType.CONTRACT)
        self.doc.document.name = "documents/a01_contract.docx"
        self.doc.save(update_fields=["document"])
        # CV i profilovka s reálným (zdvojeným) prefixem `storage/` i bez něj
        self.owner_student.cv_file.name = "storage/documents/cvs/owner_cv.pdf"
        self.owner_student.profile_picture.name = "images/profiles/owner.png"
        self.owner_student.save()
        # vyučující předmětu studenta
        self.teacher = type(self.garant).objects.create_user(
            email="teacher@a01.test",
            password="a01-only-password",
            is_active=True,
            department=self.other_department,
        )
        UserSubject.objects.create(user=self.owner_student, subject=self.subject, role=UserSubjectType.Student)
        UserSubject.objects.create(user=self.teacher, subject=self.subject, role=UserSubjectType.Professor)

    def _uri(self, rel):
        return f"/storage/{rel}"

    def _check(self, user, uri):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get(CHECK_URL, HTTP_X_ORIGINAL_URI=uri)

    def test_matrix(self):
        doc = self._uri("documents/a01_contract.docx")
        cv = self._uri("documents/cvs/owner_cv.pdf")
        cv_doubled = self._uri("storage/documents/cvs/owner_cv.pdf")
        pic = self._uri("images/profiles/owner.png")
        logo = self._uri("images/logos/firma.png")
        cases = [
            # (uživatel, uri, očekávaný status)
            (self.owner_student, doc, 200),
            (self.other_student, doc, 403),
            (self.org_user, doc, 200),
            (self.foreign_org, doc, 403),
            (self.garant, doc, 200),
            (self.foreign_professor, doc, 403),
            (self.admin, doc, 200),
            (self.owner_student, cv, 200),
            (self.owner_student, cv_doubled, 200),
            (self.other_student, cv, 403),
            (self.org_user, cv, 200),  # má přihlášku studenta
            (self.foreign_org, cv, 403),
            (self.teacher, cv, 200),  # vyučuje předmět studenta
            (self.foreign_professor, cv, 403),
            (self.admin, cv, 200),
            (self.owner_student, pic, 200),
            (self.other_student, pic, 403),
            (self.foreign_org, pic, 403),
            (self.other_student, logo, 200),  # loga veřejná
            (self.owner_student, self._uri("documents/neexistuje.docx"), 403),
        ]
        for user, uri, expected in cases:
            with self.subTest(user=user.email, uri=uri):
                self.assertEqual(self._check(user, uri).status_code, expected)

    def test_traversal_and_malformed_uri_denied(self):
        bad = [
            "/storage/../etc/passwd",
            "/storage/documents/../../etc/passwd",
            "/storage/%2e%2e/etc/passwd",
            "/storage/documents/%2e%2e/%2e%2e/etc/passwd",
            "/storage/documents%2f..%2fx",
            "/storage//documents/a01_contract.docx",
            "/storage/documents\\a01_contract.docx",
            "/storage/documents/a01_contract.docx%00.png",
            "/storage/%252e%252e/x",
            "/media/documents/a01_contract.docx",
            "/storage/",
            "",
        ]
        for uri in bad:
            with self.subTest(uri=uri):
                self.assertEqual(self._check(self.admin, uri).status_code, 403)

    def test_missing_header_is_403(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        self.assertEqual(client.get(CHECK_URL).status_code, 403)

    def test_unauthenticated_is_401(self):
        response = APIClient().get(CHECK_URL, HTTP_X_ORIGINAL_URI="/storage/images/logos/x.png")
        self.assertEqual(response.status_code, 401)

    def test_query_string_is_ignored(self):
        self.assertEqual(
            self._check(self.owner_student, self._uri("documents/a01_contract.docx") + "?v=1").status_code,
            200,
        )
        self.assertEqual(
            self._check(self.other_student, self._uri("documents/a01_contract.docx") + "?v=1").status_code,
            403,
        )

    def test_view_and_check_agree(self):
        """ServeStorageFileView rozhoduje stejně jako auth_request (403 vs. 404 jen u neexistujícího souboru)."""
        for user, allowed in ((self.owner_student, True), (self.other_student, False)):
            decision = check_storage_access(user, "documents/a01_contract.docx")
            self.assertIs(decision is StorageAccess.ALLOWED, allowed)

    def test_helpers(self):
        self.assertEqual(
            canonical_rel_path("storage/storage/documents/cvs/x.pdf"),
            "documents/cvs/x.pdf",
        )
        self.assertEqual(rel_path_from_uri("/storage/documents/x.docx"), "documents/x.docx")
        self.assertIsNone(rel_path_from_uri(None))

    def test_middleware_uses_same_decision(self):
        from django.http import Http404
        from django.test import RequestFactory

        from api.middleware import DocumentPermissionMiddleware

        middleware = DocumentPermissionMiddleware(lambda r: None)
        for user, allowed in ((self.owner_student, True), (self.other_student, False)):
            request = RequestFactory().get("/storage/documents/a01_contract.docx")
            request.user = user
            with self.subTest(user=user.email):
                if allowed:
                    self.assertIsNone(middleware.process_view(request, None, (), {}))
                else:
                    with self.assertRaises(Http404):
                        middleware.process_view(request, None, (), {})
