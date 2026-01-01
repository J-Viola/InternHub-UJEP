from django.http import FileResponse
from django.utils import timezone  # Import timezone from django.utils
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.permissions import IsOrganizationOwner
from practices.models import Practice
from student_practices.models import (
    DocumentHelper,
    EmployerInvitation,
    StudentPractice,
    UploadedDocument,
)
from student_practices.permissions import (
    HasDocumentAccess,
    IsPracticeOrganizationOwner,
    IsSubjectTeacherOrHeadForPractice,
)
from student_practices.services import StudentPracticeService
from users.models import ApprovalStatus

from .serializers import (
    CreateInvitationSerializer,
    EmployerInvitationApprovalSerializer,
    EmployerInvitationSerializer,
    ListStudentPracticeSerializer,
    StudentPracticeCardSerializer,
)


@extend_schema(tags=["Employer Invitations"])
class EmployerInvitationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployerInvitationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return EmployerInvitation.objects.all()
        if hasattr(user, "employer_profile") and user.employer_profile:
            return EmployerInvitation.objects.filter(employer=user.employer_profile)
        return EmployerInvitation.objects.none()

    @extend_schema(summary="List all employer invitations")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Create an employer invitation")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Get employer invitation detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Update an employer invitation")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Partial update an employer invitation")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Delete an employer invitation")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    @extend_schema(
        summary="Create employer invitations for students",
        description="Creates pending invitations for specified students to a specific practice. **Permissions: Organization Owner**",
        tags=["Student Practices"],
        request=CreateInvitationSerializer,
        responses={201: OpenApiResponse(description="Invitations created successfully")},
    )
    def post(self, request):
        serializer = CreateInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        practice_id = serializer.validated_data["practice_id"]
        student_ids = serializer.validated_data["student_ids"]

        try:
            result = StudentPracticeService.create_invitations(request.user, practice_id, student_ids)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmployerInvitationApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Approve or reject an employer invitation",
        description="Processes a student's response to an employer invitation (ACCEPT/REJECT). **Permissions: Authenticated Student**",
        tags=["Student Practices"],
        request=EmployerInvitationApprovalSerializer,
        responses={200: OpenApiResponse(description="Invitation processed")},
    )
    def post(self, request):
        """
        Schválí nebo zamítne employer_invitation a případně vytvoří StudentPractice záznam
        """
        serializer = EmployerInvitationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invitation_id = serializer.validated_data["invitation_id"]
        action = serializer.validated_data["action"]

        result = StudentPracticeService.process_invitation_approval(request.user, invitation_id, action)
        return Response(result, status=status.HTTP_200_OK)


class AdminPracticeListView(generics.ListAPIView):
    @extend_schema(
        summary="List pending student practices (Admin)",
        description="Returns a list of all student practices with PENDING approval status. **Permissions: Admin/Staff**",
        tags=["Student Practices - Admin"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = [IsAuthenticated]
    serializer_class = ListStudentPracticeSerializer
    queryset = StudentPractice.objects.all()

    def get_queryset(self):
        return StudentPractice.objects.filter(approval_status=ApprovalStatus.PENDING)


class StudentPracticeListView(generics.ListAPIView):
    @extend_schema(
        summary="List student practices by practice ID",
        description="Returns all student practices (applications) for a specific practice. **Permissions: Authenticated User**",
        tags=["Student Practices"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = (IsAuthenticated,)
    serializer_class = ListStudentPracticeSerializer

    def get_queryset(self):
        # Tohle má být probíhajících praxí po prokliknutí na specifickou praxi
        practice_id = self.kwargs.get("practice_id")

        if not practice_id:
            raise ValidationError({"error": "practice_id is required"})

        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            raise NotFound({"error": "Practice not found"})

        # Filter student practices by practice_id
        return StudentPractice.objects.filter(practice=practice).all()


class OrganizationApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get pending applications for organization",
        description=(
            "Returns a list of all pending student applications for the practices belonging to the logged-in organization. "
            "**Permissions: Organization User**"
        ),
        tags=["Student Practices"],
        responses={200: ListStudentPracticeSerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        # Zjisti employer_profile id z přihlášeného uživatele (OrganizationUser)
        employer_profile = getattr(user, "employer_profile", None)
        if not employer_profile:
            return Response(
                {"detail": "Uživatel není přiřazen k žádné organizaci."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Najdi všechny praxe patřící této organizaci
        practices = Practice.objects.filter(employer=employer_profile)
        # Najdi všechny přihlášky na tyto praxe, pouze s approval_status PENDING
        student_practices = StudentPractice.objects.filter(practice__in=practices, approval_status=ApprovalStatus.PENDING)

        serializer = ListStudentPracticeSerializer(student_practices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentPracticeStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPractice
        fields = ["approval_status", "progress_status"]
        extra_kwargs = {
            "approval_status": {"required": False},
            "progress_status": {"required": False},
        }


class StudentPracticeStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsPracticeOrganizationOwner | IsSubjectTeacherOrHeadForPractice | permissions.IsAdminUser]

    @extend_schema(
        summary="Update student practice status",
        description=(
            "Updates the approval or progress status of a student practice. "
            "**Permissions: Practice Organization Owner, Subject Teacher, or Admin**"
        ),
        tags=["Student Practices"],
        request=StudentPracticeStatusUpdateSerializer,
        responses={200: StudentPracticeStatusUpdateSerializer},
    )
    def patch(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)

        self.check_object_permissions(request, student_practice)

        serializer = StudentPracticeStatusUpdateSerializer(student_practice, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentPracticeUploadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = ("document",)

    def validate_document(self, uploaded_file):
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        if ext not in ("doc", "docx"):
            raise serializers.ValidationError("Jenom Word (.doc, .docx) dokumenty jsou povoleny.")
        return uploaded_file

    def update(self, instance, validated_data):
        if instance.document:
            instance.document.delete(save=False)

        file = validated_data["document"]
        file.name = DocumentHelper.create_name_for_document(instance.document_type, instance.student_practice.user.user_id, file.name)
        instance.document = file
        instance.uploaded_at = timezone.now()  # Use timezone.now()
        instance.save()
        return instance


class StudentPracticeUploadDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, HasDocumentAccess]

    @extend_schema(
        summary="Upload a document for a student practice",
        description=(
            "Uploads a file and attaches it to the specified StudentPractice record. "
            "**Permissions: Student (Owner) or Authorized Personnel**"
        ),
        tags=["Documents"],
        parameters=[
            OpenApiParameter(
                name="document_id",
                location=OpenApiParameter.PATH,
                type=int,
                description="ID of the student practice",
            ),
        ],
        request=StudentPracticeUploadDocumentSerializer,
        responses={
            201: OpenApiResponse(description="Document successfully uploaded"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="StudentPractice not found"),
        },
    )
    def post(self, request, document_id):
        document = get_object_or_404(UploadedDocument, pk=document_id)
        self.check_object_permissions(request, document)

        serializer = StudentPracticeUploadDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Dokument byl úspěšně nahrán."}, status=status.HTTP_201_CREATED)


class StudentPracticeDownloadDocumentView(APIView):
    permission_classes = [IsAuthenticated, HasDocumentAccess]

    @extend_schema(
        summary="Download a document",
        description="Streams the file associated with the given UploadedDocument ID. **Permissions: Owner or Authorized Personnel**",
        tags=["Documents"],
        parameters=[
            OpenApiParameter(
                name="document_id",
                location=OpenApiParameter.PATH,
                type=int,
                description="ID of the uploaded document",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Binary stream of the requested file",
            ),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="UploadedDocument not found"),
        },
    )
    def get(self, request, document_id):
        document = get_object_or_404(UploadedDocument, pk=document_id)
        self.check_object_permissions(request, document)

        file_handle = document.document.open("rb")
        return FileResponse(file_handle, as_attachment=True, filename=document.document.name)


class StudentPracticeCardView(APIView):
    @extend_schema(
        summary="Get student practice card",
        description="Returns detailed information about a specific student practice. **Permissions: Authenticated User**",
        tags=["Student Practices"],
        parameters=[
            OpenApiParameter(
                name="student_practice_id",
                location=OpenApiParameter.PATH,
                type=int,
                description="ID of the student practice",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=StudentPracticeCardSerializer,
                description="Student practice details",
            ),
            404: OpenApiResponse(description="StudentPractice not found"),
        },
    )
    def get(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)

        serializer = StudentPracticeCardSerializer(student_practice)
        return Response(serializer.data, status=status.HTTP_200_OK)
