from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from rest_framework.pagination import PageNumberPagination


# Create your views here.
# -------------------------------------------------------------
# Nastavení vlastní stránkovací třídy pro všechny viewsety
# -------------------------------------------------------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# TODO: one day this will be used to serve documents only to related users
# (students will see their own and subject teacher + head of department)
def serve_user_file(request, path):
    # deny anonymous users
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    # build and normalize file path
    doc_root = Path(settings.STORAGE_ROOT) / "documents"
    full_path = (doc_root / path).resolve()
    # ensure the file is inside our documents directory
    if not str(full_path).startswith(str(doc_root.resolve())):
        raise Http404
    # check existence
    if not full_path.is_file():
        raise Http404
    # stream the file
    return FileResponse(open(full_path, "rb"))
