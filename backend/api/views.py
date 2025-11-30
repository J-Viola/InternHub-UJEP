from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all API viewsets"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def serve_user_file(request, path):
    """
    Serve user documents with authentication and path validation.

    TODO: Implement granular permissions (students see their own documents,
    subject teachers and department heads see related documents)
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    # Build and normalize file path
    doc_root = Path(settings.STORAGE_ROOT) / "documents"
    full_path = (doc_root / path).resolve()

    # Ensure the file is inside our documents directory (security check)
    if not str(full_path).startswith(str(doc_root.resolve())):
        raise Http404("Invalid path")

    # Check file existence
    if not full_path.is_file():
        raise Http404("File not found")

    # Stream the file
    return FileResponse(full_path.open("rb"))
