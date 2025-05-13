import base64
import json
import logging
import re

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from users.dtos.dtos import EkonomickySubjektDTO
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def login(request):
    """Redirect to STAG login page"""
    callback_url = request.build_absolute_uri("/api/users/auth-callback/")
    login_url = (
        f"{settings.STAG_WS_URL}/login?originalURL={callback_url}?basicAuth=1"
    )

    # Add long ticket parameter if needed
    if request.GET.get("longTicket"):
        login_url += "&longTicket=1"

    # # Use main login method if configured
    # if getattr(settings, 'STAG_ONLY_MAIN_LOGIN_METHOD', False):
    #     login_url += "&onlyMainLoginMethod=1"
    # response = redirect(login_url)
    # auth_credentials = "indy:demo"
    # auth_bytes = auth_credentials.encode('utf-8')
    # auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    # auth_header = f"Basic {auth_b64}"
    # response.headers['Authorization'] = auth_header

    auth_credentials = "indy:demo"
    auth_bytes = auth_credentials.encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
    auth_header = f"Basic {auth_b64}"
    headers = {"Authorization": auth_header}

    response = requests.get(login_url, headers=headers)
    if response.status_code == 200:
        return HttpResponse(response.text)
    else:
        return JsonResponse(
            {
                "error": f"Login request failed with status {response.status_code}"
            },
            status=500,
        )


@csrf_exempt
def auth_callback(request):
    """Handle callback from STAG authentication"""
    ticket = request.POST.get("ticket")

    if not ticket or ticket == "anonymous":
        return JsonResponse({"error": "Authentication failed"}, status=401)

    try:
        # Decode base64 user info
        # Store authentication data in session
        request.session["stag_user_ticket"] = ticket

        try:

            # Construct the URL for getStagUserListForLoginTicket
            stag_api_url = f"{settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"

            # Make the request with the ticket
            response = requests.get(
                stag_api_url,
                params={"ticket": ticket, "longTicket": "1"},
                timeout=(3.05, 27),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200:
                # Process the response and store it
                stag_user_details = response.json()
                request.session["stag_user_details"] = stag_user_details
                logger.info(
                    f"Retrieved additional user details for ticket {ticket}"
                )
            else:
                logger.warning(
                    f"Failed to get user details from STAG WS: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error requesting STAG user details: {str(e)}")
        # response = redirect(settings.FRONTEND_URL + "?auth_success=true")
        # response.set_cookie(
        #     "session_id",
        #     request.session.session_key,
        #     httponly=True,
        #     secure=True,
        # )
        # Redirect to frontend with success
        return JsonResponse({
            "a":stag_user_details
        },
            status=200,
            safe=False
        )

        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to process authentication data {str(e)}"},
            status=400,
        )


#
# def check_auth(request):
#     """Check if user is authorized"""
#     ticket = request.session.get('stag_user_ticket')
#     roles = request.session.get('stag_user_roles', [])
#
#     if not ticket or not roles:
#         return JsonResponse({'authorized': False}, status=401)
#
#     return JsonResponse({
#         'authorized': True,
#         'roles': roles,
#         'user': request.session.get('stag_user_info')
#     })
#
#
# def logout(request):
#     """Clear session data"""
#     for key in ['stag_user_ticket', 'stag_user_info', 'stag_user_roles']:
#         if key in request.session:
#             del request.session[key]
#
#     request.session.flush()
#     return JsonResponse({'logged_out': True})


@login_required
def aresJustice(request):
    ico = request.GET.get("ico")
    if not ico:
        return JsonResponse({"error": "IČO parameter is missing"}, status=400)

    if not re.fullmatch(r"\d{8}", ico):
        return JsonResponse(
            {"error": "Invalid IČO format. It must be 8 digits."}, status=400
        )

    cache_key = f"ares_{ico}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    response = requests.get(
        "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/"
        + ico
    )

    if response.status_code == 200:
        data = response.json()
        ares_dto = EkonomickySubjektDTO.model_validate(data)
        cache.set(cache_key, ares_dto, timeout=3600)
        return JsonResponse(data)
    else:
        return JsonResponse(
            {"error": "Failed to fetch data from ARES"},
            status=response.status_code,
        )


@login_required
def update_ares_subject(request):
    ico = request.GET.get("ico")
    if not ico:
        return JsonResponse({"error": "IČO parameter is missing"}, status=400)

    if not re.fullmatch(r"\d{8}", ico):
        return JsonResponse(
            {"error": "Invalid IČO format. It must be 8 digits."}, status=400
        )

    cache_key = f"ares_{ico}"
    ares_data = cache.get(cache_key)

    if not ares_data:
        # Request data from ARES using GET with ico as parameter.
        response = requests.get(
            "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/"
            + ico
        )
        if response.status_code == 200:
            response_data = response.json()
            if "kod" in response_data and response_data["kod"] != None:
                return JsonResponse(
                    {"error": response_data["kod"]}, status=400
                )
            ares_data = EkonomickySubjektDTO.model_validate(response_data)
            cache.set(cache_key, ares_data, timeout=3600)
        else:
            return JsonResponse(
                {"error": "Failed to fetch data from ARES"},
                status=response.status_code,
            )

    # Update current logged user with the ARES subject information.
    # It is assumed that the user model includes an 'ares_subject' field.
    user = request.user
    user.ares_subject = ares_data
    user.save()

    # Return the subject information as JSON.
    return JsonResponse(ares_data)
