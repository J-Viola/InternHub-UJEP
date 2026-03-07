from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters as drf_filters
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.views import StandardResultsSetPagination
from users.messages import UserMessages
from users.models import (
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StagUser,
    StudentUser,
    User,
)
from users.permissions import (
    CanViewStudentProfile,
    IsOrganizationOwner,
    IsOrganizationUser,
    IsStagTeacher,
)
from users.services import fetch_ares_data, update_organization_from_ares
from users.throttling import LoginThrottle, PasswordResetThrottle

from .serializers import (
    AdminOrganizationSerializer,
    AllStudentsListSerializer,
    AresJusticeSerializer,
    AresRequestSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    OrganizationRegisterSerializer,
    OrganizationUserListSerializer,
    OrganizationUserProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
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
    throttle_classes = [AnonRateThrottle] if not settings.DEBUG else []

    @extend_schema(
        summary="Register a new organization user",
        responses={201: OpenApiResponse(description="User registered successfully")},
    )
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


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle] if not settings.DEBUG else []

    @extend_schema(
        summary="Request password reset email",
        tags=["Auth"],
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="If email exists, reset link was sent")},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            # STAG users cannot reset password here
            if isinstance(user, StagUser):
                return Response(
                    {"detail": UserMessages.STAG_PASSWORD_CHANGE_DISABLED},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # URL na frontend (např. http://localhost:3000/reset-password/UID/TOKEN)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            reset_url = f"{frontend_url}/reset-password/{uid}/{token}"

            send_mail(
                "Obnova hesla - InternHub UJEP",
                f"Pro obnovu hesla klikněte na tento odkaz: {reset_url}\n\nPokud jste o obnovu nežádali, tento email ignorujte.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            # Pro bezpečnost neříkáme, že email neexistuje
            pass

        return Response(
            {"message": "Pokud email v systému existuje, byl na něj odeslán odkaz pro obnovu hesla."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm password reset",
        tags=["Auth"],
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset successful")},
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uidb64"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": UserMessages.INVALID_LINK}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response(
                {"detail": UserMessages.INVALID_TOKEN},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(
            {"message": "Heslo bylo úspěšně změněno. Nyní se můžete přihlásit."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change user password",
        description="Changes the password for the currently logged-in user. **Permissions: Authenticated User (Non-STAG)**",
        tags=["Auth"],
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
    )
    def post(self, request):
        user = request.user
        if isinstance(user, StagUser):
            return Response(
                {"detail": UserMessages.STAG_PASSWORD_CHANGE_DISABLED},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["INVALID_PASSWORD"]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "PASSWORD_CHANGED_SUCCESS"}, status=status.HTTP_200_OK)


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
        request=AresRequestSerializer,
        responses={200: OrganizationUserProfileSerializer},
    )
    def post(self, request):
        serializer = AresRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ico = serializer.validated_data["ico"]

        try:
            user = update_organization_from_ares(request.user, ico)
            serializer = OrganizationUserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle] if not settings.DEBUG else []

    @extend_schema(
        summary="Login / Obtain JWT Token",
        description="Authenticates a user and returns access and refresh JWT tokens along with user info. **Permissions: Allow Any**",
        tags=["Auth"],
        responses={200: TokenResponseSerializer},
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


@extend_schema_view(
    get=extend_schema(
        summary="List users in organization",
        description="Returns a list of all users associated with the same organization as the current user."
        "**Permissions: Organization User or Admin**",
        tags=["Users"],
    )
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
                raise serializers.ValidationError({"detail": UserMessages.ORGANIZATION_MISSING})

            org_id = employer_profile.employer_id
            return OrganizationUser.objects.filter(employer_profile_id=org_id).select_related("employer_profile")


class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated, CanViewStudentProfile]

    @extend_schema(
        summary="Get student profile detail",
        responses={
            200: StudentProfileSerializer,
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        try:
            student = StudentUser.objects.get(pk=student_id)
        except StudentUser.DoesNotExist:
            return Response({"detail": UserMessages.STUDENT_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, student)
        serializer = StudentProfileSerializer(student, context={"request": request})
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="List all students (paginated)",
        description="Returns a paginated list of all active students in the system. **Permissions: Authenticated User**",
        tags=["Users"],
    )
)
class AllStudentsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AllStudentsListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [drf_filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "os_cislo"]

    def get_queryset(self):
        return StudentUser.objects.filter(is_active=True).select_related("stag_role").prefetch_related("user_subjects__subject__department")


@extend_schema_view(
    list=extend_schema(summary="List all organizations (Admin)"),
    retrieve=extend_schema(summary="Get organization detail (Admin)"),
    create=extend_schema(
        summary="Register a new organization (Admin)",
        request=OrganizationRegisterSerializer,
    ),
    update=extend_schema(summary="Update organization detail (Admin)"),
    partial_update=extend_schema(summary="Partial update organization detail (Admin)"),
    destroy=extend_schema(summary="Delete an organization (Admin)"),
)
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

    def create(self, request, *args, **kwargs):
        serializer = OrganizationRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if hasattr(user, "employer_profile"):
            return Response(
                self.get_serializer(user.employer_profile).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        description="Returns the profile details of the currently logged-in user (Student, Professor, or Organization)."
        "**Permissions: Authenticated User**",
        tags=["Users"],
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        user = request.user
        context = {"request": request}

        if isinstance(user, StudentUser):
            serializer = StudentUserProfileSerializer(user, context=context)
        elif isinstance(user, ProfessorUser):
            serializer = ProfessorUserProfileSerializer(user, context=context)
        elif isinstance(user, OrganizationUser):
            serializer = OrganizationUserProfileSerializer(user, context=context)
        else:
            serializer = UserProfileSerializer(user, context=context)

        return Response(serializer.data)

    @extend_schema(
        summary="Update current user profile",
        description="Updates the profile details of the currently logged-in user. **Permissions: Authenticated User**",
        tags=["Users"],
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
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
