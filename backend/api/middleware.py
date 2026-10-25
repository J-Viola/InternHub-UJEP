from django.conf import settings
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from api.file_access import StorageAccess, check_storage_access, rel_path_from_uri


class DocumentPermissionMiddleware(MiddlewareMixin):
    """Druhá vrstva kontroly pro ``/storage/`` obsluhované Djangem (``DEBUG``).

    A-25: rozhoduje stejná funkce ``check_storage_access`` jako ``ServeStorageFileView``
    a ``StorageAuthCheckView``; nepřihlášený i nepovolený přístup se neprozrazuje (403/404).
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.path.startswith(f"/{settings.STORAGE_URL}"):
            return None

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        rel = rel_path_from_uri(request.path)
        if rel is None:
            raise Http404()
        if check_storage_access(request.user, rel) is not StorageAccess.ALLOWED:
            raise Http404()
        return None
