from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import base64
import json
import logging

logger = logging.getLogger(__name__)


def index(request):
    return JsonResponse(str(request.session.items()), safe=False)