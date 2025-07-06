from api.models import UploadedDocument
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class DocumentPermissionMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        prefix = f"{settings.STORAGE_URL}documents/"
        if request.path.startswith(prefix):
            if not request.user.is_authenticated:
                return HttpResponseForbidden()
            url_length = len(settings.STORAGE_URL)
            rel_path = request.path[url_length:]
            allowed = (
                UploadedDocument.objects.filter(document=rel_path)
                .filter(
                    Q(practice__contact_user=request.user)
                    | Q(practice__practiceuser__user=request.user)
                    | Q(practice__studentpractice__user=request.user)
                )
                .exists()
            )
            if not allowed:
                raise Http404()
        return None
