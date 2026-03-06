from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from student_practices.models import StudentPractice, UploadedDocument


class DocumentPermissionMiddleware(MiddlewareMixin):
    """Restrict document file access to authorised users only."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        prefix = f"/{settings.STORAGE_URL}documents/"

        if not request.path.startswith(prefix):
            return None

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        # DB stores paths without leading slash, e.g. "storage/documents/file.docx"
        rel_path = request.path.lstrip("/")

        # Step 1: resolve path → document PK (uses index on ``document`` column)
        doc = UploadedDocument.objects.filter(document=rel_path).only("document_id").first()
        if doc is None:
            raise Http404()

        # Step 2: check that the requesting user is associated with this document
        has_access = (
            StudentPractice.objects.filter(
                Q(contract_document_id=doc.document_id) | Q(content_document_id=doc.document_id) | Q(feedback_document_id=doc.document_id)
            )
            .filter(Q(user=request.user) | Q(practice__contact_user=request.user) | Q(practice__employer__organization_users=request.user))
            .exists()
        )

        if not has_access:
            raise Http404()

        return None
