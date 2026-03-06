import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def index(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"detail": "Not found."}, status=404)
    return JsonResponse({"session_keys": list(request.session.keys())})
