import re

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.decorators import role_required
from api.models import (
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)
from api.views import StandardResultsSetPagination
from users.permissions import CanViewStudentProfile
from users.services import fetch_ares_data, update_organization_from_ares

from .models import StagRoleEnum
from .serializers import (
    AdminOrganizationSerializer,
    AllStudentsListSerializer,
    AresJusticeSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    OrganizationRegisterSerializer,
    OrganizationUserListSerializer,
    OrganizationUserProfileSerializer,
    ProfessorUserProfileSerializer,
    StudentProfileSerializer,
    StudentUserProfileSerializer,
    TokenResponseSerializer,
    UserInfoSerializer,
    UserProfileSerializer,
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

        ares_data = fetch_ares_data(ico)

        if ares_data:
            return Response(ares_data.model_dump(), status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Failed to fetch data from ARES"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateAresSubjectView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required([OrganizationRole.OWNER])
    def post(self, request):
        ico = request.data.get("ico")
        if not ico:
            return Response(
                {"error": "IČO parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not re.fullmatch(r"\d{8}", str(ico)):
            return Response(
                {"error": "Invalid IČO format. It must be 8 digits."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = update_organization_from_ares(request.user, ico)
            serializer = OrganizationUserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(responses={200: TokenResponseSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data
        user = tokens["user"]

        user_info_serializer = UserInfoSerializer(user)

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": user_info_serializer.data,
            }
        )


class OrganizationUserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationUserListSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return OrganizationUser.objects.all().select_related("employer_profile")
        else:
            employer_profile = getattr(user, "employer_profile", None)
            if not employer_profile:
                return OrganizationUser.objects.none()

            org_id = employer_profile.employer_id
            return OrganizationUser.objects.filter(employer_profile_id=org_id).select_related("employer_profile")

    def list(self, request, *args, **kwargs):
        user = self.request.user
        if not getattr(user, "is_superuser", False) and not getattr(user, "employer_profile", None):
            return Response(
                {"detail": "Uživatel nemá přiřazenou organizaci."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().list(request, *args, **kwargs)


class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated, CanViewStudentProfile]

    @extend_schema(responses={200: StudentProfileSerializer})
    def get(self, request, student_id):
        try:
            student = StudentUser.objects.get(pk=student_id)
        except StudentUser.DoesNotExist:
            return Response({"detail": "Student nenalezen."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, student)
        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)


class AllStudentsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AllStudentsListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return StudentUser.objects.filter(is_active=True).select_related("stag_role").prefetch_related("user_subjects__subject__department")


class AdminOrganizationViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminOrganizationSerializer

    queryset = EmployerProfile.objects.all()
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        departments = self.queryset
        page = self.paginate_queryset(departments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        department = self.get_object()
        serializer = self.get_serializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = OrganizationRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if hasattr(user, "employer_profile"):
            return Response(self.get_serializer(user.employer_profile).data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def update(self, request, pk=None, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def partial_update(self, request, pk=None, *args, **kwargs):
        return self.update(request, pk, partial=True, *args, **kwargs)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def destroy(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request):
        user = request.user

        if isinstance(user, StudentUser):
            serializer = StudentUserProfileSerializer(user)
        elif isinstance(user, ProfessorUser):
            serializer = ProfessorUserProfileSerializer(user)
        elif isinstance(user, OrganizationUser):
            serializer = OrganizationUserProfileSerializer(user)
        else:
            serializer = UserProfileSerializer(user)

        return Response(serializer.data)

    @extend_schema(request=UserProfileSerializer, responses={200: UserProfileSerializer})
    def patch(self, request):
        user = request.user

        if isinstance(user, StudentUser):
            serializer = StudentUserProfileSerializer(user, data=request.data, partial=True)
        elif isinstance(user, ProfessorUser):
            serializer = ProfessorUserProfileSerializer(user, data=request.data, partial=True)
        elif isinstance(user, OrganizationUser):
            serializer = OrganizationUserProfileSerializer(user, data=request.data, partial=True)
        else:
            serializer = UserProfileSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
