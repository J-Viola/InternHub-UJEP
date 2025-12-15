from django.http import FileResponse
from django.utils import timezone  # Import timezone from django.utils
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
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
from student_practices.permissions import HasDocumentAccess
from student_practices.services import StudentPracticeService
from users.models import ApprovalStatus

from .serializers import (
    CreateInvitationSerializer,
    EmployerInvitationApprovalSerializer,
    EmployerInvitationSerializer,
    ListStudentPracticeSerializer,
    StudentPracticeCardSerializer,
)


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


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]

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
    permission_classes = [IsAuthenticated]
    serializer_class = ListStudentPracticeSerializer
    queryset = StudentPractice.objects.all()

    def get_queryset(self):
        return StudentPractice.objects.filter(approval_status=ApprovalStatus.PENDING)


class StudentPracticeListView(generics.ListAPIView):
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
    permission_classes = [IsAuthenticated]

    def patch(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)

        # Check permissions: Only the organization that owns the practice can change status
        is_owner_org = hasattr(request.user, "employer_profile") and student_practice.practice.employer == request.user.employer_profile

        if not is_owner_org and not request.user.is_superuser:
            return Response(
                {"detail": "Nemáte oprávnění k úpravě statusu této praxe."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        description="Uploads a file and attaches it to the specified StudentPractice record.",
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
        description="Streams the file associated with the given UploadedDocument ID.",
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
        description="Returns detailed information about a specific student practice.",
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
