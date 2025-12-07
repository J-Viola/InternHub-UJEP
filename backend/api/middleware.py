from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from student_practices.models import StudentPractice


class DocumentPermissionMiddleware(MiddlewareMixin):
    """Middleware to restrict document access to authorized users only"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        prefix = f"{settings.STORAGE_URL}documents/"

        if not request.path.startswith(prefix):
            return None

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        # Extract relative path from URL
        # rel_path must match what is stored in DB (e.g., "documents/contract_....docx")
        # settings.STORAGE_URL is usually "storage/"
        # request.path is "/storage/documents/..."

        # If MEDIA_URL/STORAGE_URL is "storage/", then:
        # DB stores: "documents/file.docx" (because upload_to=STORAGE_URL + "documents") -> Wait, upload_to="storage/documents"
        # Let's check model: upload_to=settings.STORAGE_URL + "documents" -> "storage/documents"

        # So DB stores: "storage/documents/filename.docx"
        # Request path: "/storage/documents/filename.docx"

        rel_path = request.path.lstrip("/")

        # Check if user has access to this document
        # We search for a StudentPractice that links to this document
        has_access = (
            StudentPractice.objects.filter(
                Q(contract_document__document=rel_path) | Q(content_document__document=rel_path) | Q(feedback_document__document=rel_path)
            )
            .filter(Q(user=request.user) | Q(practice__contact_user=request.user) | Q(practice__employer__organization_users=request.user))
            .exists()
        )

        if not has_access:
            raise Http404()

        return None
