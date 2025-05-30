import re

import requests
from api.models import EmployerProfile, Status
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from users.dtos.dtos import EkonomickySubjektDTO

from .serializers import CustomTokenObtainPairSerializer, LogoutSerializer, RegisterSerializer


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
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aresJustice(request):
    ico = request.GET.get("ico")
    if not ico:
        return JsonResponse({"error": "IČO parameter is missing"}, status=400)

    if not re.fullmatch(r"\d{8}", ico):
        return JsonResponse({"error": "Invalid IČO format. It must be 8 digits."}, status=400)

    cache_key = f"ares_{ico}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    response = requests.get("https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/" + ico)

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


@api_view(["POST"])
@login_required
def update_ares_subject(request):

    if EmployerProfile.objects.get(employer_id=request.user.id) is not None:
        return JsonResponse({"error": "User already has employer profile"}, status=400)

    ico = request.POST.get("ico")
    company_profile = request.POST.get("company_profile")
    if not ico:
        return JsonResponse({"error": "IČO parameter is missing"}, status=400)

    if not re.fullmatch(r"\d{8}", ico):
        return JsonResponse({"error": "Invalid IČO format. It must be 8 digits."}, status=400)

    cache_key = f"ares_{ico}"
    ares_data = cache.get(cache_key)

    if not ares_data:
        response = requests.get("https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/" + ico)
        if response.status_code == 200:
            response_data = response.json()
            if "kod" in response_data and response_data["kod"] is not None:
                return JsonResponse({"error": response_data["kod"]}, status=400)
            ares_data = EkonomickySubjektDTO.model_validate(response_data)
            cache.set(cache_key, ares_data, timeout=3600)
        else:
            return JsonResponse(
                {"error": "Failed to fetch data from ARES"},
                status=response.status_code,
            )

    user = request.user
    employer_profile = EmployerProfile.objects.get(employer_id=user.id)
    if not employer_profile:
        status = Status.objects.get(status_name="Pending")
        assert status is not None, "Status 'Pending' must exist in the database"
        EmployerProfile.objects.create(
            employer_id=user.id,
            ico=ares_data.ico,
            dic=ares_data.dic,
            name=ares_data.obchodniJmeno,
            street=ares_data.sidlo.textAdresy,
            zip_code=ares_data.sidlo.psc,
            company_profile=company_profile,
            approval_status=status,
        )
    user.save()

    return JsonResponse(user)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
