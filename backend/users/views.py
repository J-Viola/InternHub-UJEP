import re

import requests
from api.decorators import role_required
from api.models import ApprovalStatus, EmployerProfile, OrganizationRole, OrganizationUser, StudentUser, ProfessorUser
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from users.dtos.dtos import EkonomickySubjektDTO

from .serializers import (
    AresJusticeSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    OrganizationRegisterSerializer,
    StudentProfileSerializer,
    TokenResponseSerializer,
    UserProfileSerializer,
    StudentUserProfileSerializer,
    ProfessorUserProfileSerializer,
    OrganizationUserProfileSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = OrganizationRegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
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


class AresJusticeView(generics.GenericAPIView):
    serializer_class = AresJusticeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ico = serializer.validated_data.get("ico")
        cache_key = f"ares_{ico}"
        cached_data = cache.get(cache_key)
        if cached_data:
            ares_dto = EkonomickySubjektDTO.model_validate(cached_data)
            return JsonResponse(ares_dto.model_dump(), safe=False)

        response = requests.get("https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/" + ico)

        if response.status_code == 200:
            data = response.json()
            ares_dto = EkonomickySubjektDTO.model_validate(data)
            cache.set(cache_key, ares_dto.model_dump(), timeout=3600)
            return JsonResponse(ares_dto.model_dump(), safe=False)
        else:
            return JsonResponse(
                {"error": "Failed to fetch data from ARES"},
                status=response.status_code,
            )


# TODO not finished endpoint
@api_view(["POST"])
@login_required
@role_required([OrganizationRole.OWNER])
def update_ares_subject(request):

    ico = request.POST.get("ico")
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
            cache.set(cache_key, ares_data.model_dump(), timeout=3600)
        else:
            return JsonResponse(
                {"error": "Failed to fetch data from ARES"},
                status=response.status_code,
            )

    user = request.user
    employer_profile = EmployerProfile.objects.get(employer_id=user.id)
    if not employer_profile:
        status = ApprovalStatus.PENDING
        EmployerProfile.objects.create(
            employer_id=user.id,
            ico=ares_data.ico,
            dic=ares_data.dic,
            name=ares_data.obchodniJmeno,
            street=ares_data.sidlo.textovaAdresa,
            zip_code=ares_data.sidlo.psc,
            approval_status=status,
        )
    user.save()

    return JsonResponse(user)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(responses={200: TokenResponseSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data

        user = tokens["user"]

        # Debug: Zkontrolujme role při přihlášení
        print(f"DEBUG: Login - user type: {type(user)}")
        print(f"DEBUG: Login - organization_role: {getattr(user, 'organization_role', 'N/A')}")
        print(f"DEBUG: Login - role property: {user.role}")

        user_info = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "firstName": user.first_name,
            "lastName": user.last_name,
        }

        serializer = TokenResponseSerializer(
            data={
                "refresh": tokens["refresh"],
                "access": tokens["access"],
                "user": user_info,
            }
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrganizationUserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        employer_profile = getattr(user, "employer_profile", None)
        if not employer_profile:
            return Response({"detail": "Uživatel nemá přiřazenou organizaci."}, status=status.HTTP_400_BAD_REQUEST)
        org_id = employer_profile.employer_id
        users = OrganizationUser.objects.filter(employer_profile_id=org_id)
        data = []
        for u in users:
            role = None
            if u.organization_role is not None:
                # Pokud je to integer, převedeme na enum
                if isinstance(u.organization_role, int):
                    try:
                        role = OrganizationRole(u.organization_role).name
                    except Exception:
                        role = str(u.organization_role)
                # Pokud je to enum
                elif hasattr(u.organization_role, "name"):
                    role = u.organization_role.name
                # Pokud je to ForeignKey na OrganizationRole model
                elif hasattr(u.organization_role, "role_name") and u.organization_role.role_name:
                    role = u.organization_role.role_name
                elif hasattr(u.organization_role, "role") and u.organization_role.role:
                    role = u.organization_role.role
                else:
                    role = str(u.organization_role)
            data.append({"id": u.id, "name": f"{u.first_name} {u.last_name}", "role": role})
        return Response(data)


class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: StudentProfileSerializer})
    def get(self, request, student_id):
        try:
            from api.models import StudentUser

            student = StudentUser.objects.get(pk=student_id)
        except StudentUser.DoesNotExist:
            return Response({"detail": "Student nenalezen."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request):
        user = request.user
        
        # Vybereme správný serializer podle typu uživatele
        if isinstance(user, StudentUser):
            serializer = StudentUserProfileSerializer(user)
        elif isinstance(user, ProfessorUser):
            serializer = ProfessorUserProfileSerializer(user)
        elif isinstance(user, OrganizationUser):
            serializer = OrganizationUserProfileSerializer(user)
        else:
            serializer = UserProfileSerializer(user)
        
        return Response(serializer.data)
