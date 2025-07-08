import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def index(request):
    return JsonResponse(str(request.session.items()), safe=False)
