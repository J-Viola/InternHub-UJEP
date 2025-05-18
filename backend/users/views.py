import re

import requests
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from users.dtos.dtos import EkonomickySubjektDTO

from .serializers import (CustomTokenObtainPairSerializer, LogoutSerializer,
                          RegisterSerializer)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"success": "Successfully logged out"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


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
            if "kod" in response_data and response_data["kod"] is not None:
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


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
