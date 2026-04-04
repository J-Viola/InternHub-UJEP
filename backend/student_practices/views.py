import logging

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.views import StandardResultsSetPagination
from practices.models import Practice
from student_practices.messages import StudentPracticeMessages
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
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus
from users.permissions import IsOrganizationOwner

from .serializers import (
    CreateInvitationSerializer,
    EmployerInvitationApprovalSerializer,
    EmployerInvitationSerializer,
    ListStudentPracticeSerializer,
    StudentPracticeCardSerializer,
)

logger = logging.getLogger(__name__)


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
        response = super().create(request, *args, **kwargs)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.CREATE,
            object_type="EmployerInvitation",
            description=f"Vytvoření pozvánky zaměstnavatelem {request.user.email}",
        )
        return response

    @extend_schema(summary="Get employer invitation detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Update an employer invitation")
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().update(request, *args, **kwargs)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.UPDATE,
            object_type="EmployerInvitation",
            object_id=instance.invitation_id,
            description=f"Úprava pozvánky ID {instance.invitation_id}",
        )
        return response

    @extend_schema(summary="Partial update an employer invitation")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Delete an employer invitation")
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.DELETE,
            object_type="EmployerInvitation",
            object_id=instance.invitation_id,
            description=f"Smazání pozvánky ID {instance.invitation_id}",
        )
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


@extend_schema_view(
    get=extend_schema(
        summary="List pending student practices (Admin)",
        description="Returns a list of all student practices with PENDING approval status. **Permissions: Admin/Staff**",
        tags=["Student Practices - Admin"],
    )
)
class AdminPracticeListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ListStudentPracticeSerializer
    queryset = StudentPractice.objects.all()

    def get_queryset(self):
        return StudentPractice.objects.filter(approval_status=ApprovalStatus.PENDING).select_related(
            "user",
            "practice__subject__department",
            "practice__employer",
        )


class ProfessorApplicationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ListStudentPracticeSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="Get pending applications for professor",
        description=(
            "Returns a list of all pending student applications that the logged-in professor "
            "is authorized to approve (as department head, subject manager, or teacher). "
            "**Permissions: Professor User**"
        ),
        tags=["Student Practices"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Q

        from users.models import DepartmentRole, ProfessorUser, UserSubjectType

        user = self.request.user
        if not isinstance(user, ProfessorUser):
            return StudentPractice.objects.none()

        # Build filter for applications the professor can approve
        # 1. As department head
        filters = Q()
        if user.department_role == DepartmentRole.HEAD and user.department:
            filters |= Q(practice__subject__department=user.department)

        # 2. As subject manager
        filters |= Q(practice__subject__subject_manager=user)

        # 3. As subject teacher
        subject_ids = user.user_subjects.filter(role=UserSubjectType.Professor).values_list("subject_id", flat=True)
        filters |= Q(practice__subject_id__in=subject_ids)

        return (
            StudentPractice.objects.filter(filters, approval_status=ApprovalStatus.PENDING)
            .select_related(
                "user",
                "practice__subject__department",
                "practice__employer",
            )
            .distinct()
        )


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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Tohle má být probíhajících praxí po prokliknutí na specifickou praxi
        practice_id = self.kwargs.get("practice_id")

        if not practice_id:
            raise ValidationError({"error": "practice_id is required"})

        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            raise NotFound({"error": "Practice not found"})

        # Filter student practices by practice_id with select_related for optimization
        return (
            StudentPractice.objects.filter(practice=practice)
            .select_related(
                "user",
                "practice__subject__department",
                "practice__employer",
            )
            .all()
        )


class OrganizationApplicationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ListStudentPracticeSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="Get pending applications for organization",
        description=(
            "Returns a list of all pending student applications for the practices belonging to the logged-in organization. "
            "**Permissions: Organization User**"
        ),
        tags=["Student Practices"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        # Zjisti employer_profile id z přihlášeného uživatele (OrganizationUser)
        employer_profile = getattr(user, "employer_profile", None)
        if not employer_profile:
            return StudentPractice.objects.none()

        # Najdi všechny přihlášky na praxe patřící této organizaci, pouze s approval_status PENDING
        return StudentPractice.objects.filter(
            practice__employer=employer_profile,
            approval_status=ApprovalStatus.PENDING,
        ).select_related(
            "user",
            "practice__subject__department",
            "practice__employer",
        )


class StudentPracticeStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPractice
        fields = ["approval_status", "progress_status"]
        extra_kwargs = {
            "approval_status": {"required": False},
            "progress_status": {"required": False},
        }


class StudentPracticeStatusUpdateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsPracticeOrganizationOwner | IsSubjectTeacherOrHeadForPractice | permissions.IsAdminUser,
    ]

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
        try:
            student_practice = StudentPracticeService.update_student_practice_status(
                user=request.user,
                student_practice_id=student_practice_id,
                data=request.data,
            )
            serializer = StudentPracticeStatusUpdateSerializer(student_practice)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Chyba při aktualizaci stavu přihlášky")
            return Response(
                {"detail": StudentPracticeMessages.INTERNAL_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StudentPracticeUploadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = ("document",)

    def validate_document(self, uploaded_file):
        from django.conf import settings

        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        if ext not in ("doc", "docx"):
            raise serializers.ValidationError(StudentPracticeMessages.INVALID_EXTENSION)

        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            mb_limit = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise serializers.ValidationError(StudentPracticeMessages.FILE_TOO_LARGE.format(size=mb_limit))

        return uploaded_file

    def update(self, instance, validated_data):
        from student_practices.models import DocumentStatus

        if instance.document:
            instance.document.delete(save=False)

        file = validated_data["document"]
        file.name = DocumentHelper.create_name_for_document(instance.document_type, instance.student_practice.user.user_id, file.name)
        instance.document = file
        instance.uploaded_at = timezone.now()  # Use timezone.now()
        instance.status = DocumentStatus.PENDING  # Reset status on re-upload
        instance.save()
        return instance


class DocumentReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = ("status", "review_note")


class DocumentReviewView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsSubjectTeacherOrHeadForPractice | permissions.IsAdminUser,
    ]

    @extend_schema(
        summary="Review a document",
        description="Allows a professor or admin to approve or reject a document with a note. "
        "**Permissions: Subject Teacher, Head, or Admin**",
        tags=["Documents"],
        request=DocumentReviewSerializer,
        responses={200: DocumentReviewSerializer},
    )
    def patch(self, request, document_id):
        try:
            status_val = request.data.get("status")
            review_note = request.data.get("review_note", "")

            if status_val is None:
                raise ValueError("Status is required")

            document = StudentPracticeService.process_document_review(
                user=request.user,
                document_id=document_id,
                status_val=int(status_val),
                review_note=review_note,
            )
            serializer = DocumentReviewSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Chyba při recenzi dokumentu")
            return Response(
                {"detail": StudentPracticeMessages.INTERNAL_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    @transaction.atomic
    def post(self, request, document_id):
        document = get_object_or_404(UploadedDocument, pk=document_id)
        self.check_object_permissions(request, document)

        serializer = StudentPracticeUploadDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.DOCUMENT_UPLOAD,
            object_type="UploadedDocument",
            object_id=document.pk,
            description=f"Nahrání dokumentu {document.document_type} (ID: {document.pk}) uživatelem {request.user.email}",
        )

        return Response(
            {"detail": StudentPracticeMessages.DOCUMENT_UPLOAD_SUCCESS},
            status=status.HTTP_201_CREATED,
        )


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

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="UploadedDocument",
            object_id=document.pk,
            description=f"Stažení dokumentu {document.document_type} (ID: {document.pk})",
        )

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
        student_practice = get_object_or_404(
            StudentPractice.objects.select_related(
                "user",
                "practice__subject__department",
                "practice__employer",
                "contract_document",
                "content_document",
                "feedback_document",
            ),
            pk=student_practice_id,
        )

        serializer = StudentPracticeCardSerializer(student_practice, context={"request": request})

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=student_practice.student_practice_id,
            description=f"Zobrazení karty přihlášky ID {student_practice.student_practice_id}",
        )

        return Response(serializer.data, status=status.HTTP_200_OK)
