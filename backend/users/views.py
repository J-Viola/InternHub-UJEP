import re

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.views import StandardResultsSetPagination
from users.models import (
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)
from users.permissions import (
    CanViewStudentProfile,
    IsOrganizationOwner,
    IsOrganizationUser,
    IsStagTeacher,
)
from users.services import fetch_ares_data, update_organization_from_ares

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

    @extend_schema(summary="Register a new organization user", responses={201: OpenApiResponse(description="User registered successfully")})
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

    @extend_schema(
        summary="Logout user",
        description="Blacklists the provided refresh token to log out the user. **Permissions: Authenticated User**",
        tags=["Auth"],
        responses={200: OpenApiResponse(description="Successfully logged out")},
    )
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

    @extend_schema(
        summary="Fetch data from ARES",
        description="Fetches organization details from the ARES database using IČO. **Permissions: Allow Any**",
        tags=["Utils"],
        responses={200: OpenApiResponse(description="Data fetched successfully")},
    )
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
    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    @extend_schema(
        summary="Update organization info from ARES",
        description="Updates the organization details (name, address) using the provided IČO and ARES API.",
        request=serializers.DictField(child=serializers.CharField(), help_text='{"ico": "12345678"}'),
        responses={200: OrganizationUserProfileSerializer},
    )
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

    @extend_schema(
        summary="Login / Obtain JWT Token",
        description="Authenticates a user and returns access and refresh JWT tokens along with user info. **Permissions: Allow Any**",
        tags=["Auth"],
        responses={200: TokenResponseSerializer}
    )
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
    @extend_schema(
        summary="List users in organization",
        description="Returns a list of all users associated with the same organization as the current user. **Permissions: Organization User or Admin**",
        tags=["Users"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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

    @extend_schema(
        summary="Get student profile detail",
        responses={200: StudentProfileSerializer, 404: OpenApiResponse(description="Student not found")},
    )
    def get(self, request, student_id):
        try:
            student = StudentUser.objects.get(pk=student_id)
        except StudentUser.DoesNotExist:
            return Response({"detail": "Student nenalezen."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, student)
        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)


class AllStudentsListView(generics.ListAPIView):
    @extend_schema(
        summary="List all students (paginated)",
        description="Returns a paginated list of all active students in the system. **Permissions: Authenticated User**",
        tags=["Users"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = [IsAuthenticated]
    serializer_class = AllStudentsListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return StudentUser.objects.filter(is_active=True).select_related("stag_role").prefetch_related("user_subjects__subject__department")


@extend_schema(tags=["Organizations - Admin"])
class AdminOrganizationViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminOrganizationSerializer

    queryset = EmployerProfile.objects.all()
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAdminUser()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), (IsOrganizationUser | IsStagTeacher)()]
        return [permissions.IsAuthenticated()]

    @extend_schema(summary="List all organizations (Admin)")
    def list(self, request, *args, **kwargs):
        departments = self.queryset
        page = self.paginate_queryset(departments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Get organization detail (Admin)")
    def retrieve(self, request, pk=None, *args, **kwargs):
        department = self.get_object()
        serializer = self.get_serializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Register a new organization (Admin)", request=OrganizationRegisterSerializer)
    def create(self, request, *args, **kwargs):
        serializer = OrganizationRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if hasattr(user, "employer_profile"):
            return Response(self.get_serializer(user.employer_profile).data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Update organization detail (Admin)")
    def update(self, request, pk=None, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Partial update organization detail (Admin)")
    def partial_update(self, request, pk=None, *args, **kwargs):
        return self.update(request, pk, partial=True, *args, **kwargs)

    @extend_schema(summary="Delete an organization (Admin)")
    def destroy(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        description="Returns the profile details of the currently logged-in user (Student, Professor, or Organization). **Permissions: Authenticated User**",
        tags=["Users"],
        responses={200: UserProfileSerializer}
    )
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

    @extend_schema(
        summary="Update current user profile",
        description="Updates the profile details of the currently logged-in user. **Permissions: Authenticated User**",
        tags=["Users"],
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer}
    )
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
