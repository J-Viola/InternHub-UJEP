from api.models import UploadedDocument
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class DocumentPermissionMiddleware(MiddlewareMixin):
    """Middleware to restrict document access to authorized users only"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        prefix = f"{settings.STORAGE_URL}documents/"

        if not request.path.startswith(prefix):
            return None

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        # Extract relative path from URL
        rel_path = request.path[len(settings.STORAGE_URL) :]

        # Check if user has access to this document
        has_access = UploadedDocument.objects.filter(
            document=rel_path
        ).filter(
            Q(practice__contact_user=request.user)
            | Q(practice__practiceuser__user=request.user)
            | Q(practice__studentpractice__user=request.user)
        ).exists()

        if not has_access:
            raise Http404()

        return None
