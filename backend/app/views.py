import base64
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def index(request):
    return JsonResponse(str(request.session.items()), safe=False)
