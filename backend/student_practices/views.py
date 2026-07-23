import logging
import random

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
from notifications.services import EmailService
from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
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
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
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
from users.models import ActionLog, ApprovalStatus
from users.permissions import (
    CanCancelStudentPractice,
    IsAdminUser,
    IsGarantPraxe,
    IsNotCancelled,
    IsOrganizationOwner,
    IsOrganizationUser,
    IsStagStudent,
    IsStagTeacher,
    IsStudentOwner,
    IsStudentPracticeAccessible,
)

from .serializers import (
    ActionLogSerializer,
    CancelStudentPracticeSerializer,
    CreateInvitationSerializer,
    EmployerInvitationApprovalSerializer,
    EmployerInvitationSerializer,
    EvaluationSerializer,
    ListStudentPracticeSerializer,
    StudentPracticeCardSerializer,
    TransitionStudentPracticeSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Employer Invitations"])
class EmployerInvitationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployerInvitationSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsOrganizationOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = EmployerInvitation.objects.select_related("user", "employer", "practice", "practice__subject__department")
        if user.is_superuser:
            return qs
        if hasattr(user, "employer_profile") and user.employer_profile:
            return qs.filter(practice__employer=user.employer_profile)
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
    """
    Lists pending student practice applications.

    Ref: CR-ARCH-3 — tightened permissions from IsAuthenticated to
    IsStagTeacher | IsGarantPraxe | IsAdminUser, and added department-scoped
    filtering so teachers/garents only see applications from their own department.
    """

    permission_classes = [IsAuthenticated, IsStagTeacher | IsGarantPraxe | IsAdminUser]
    serializer_class = ListStudentPracticeSerializer
    queryset = StudentPractice.objects.all()

    def get_queryset(self):
        user = self.request.user
        qs = StudentPractice.objects.filter(approval_status=ApprovalStatus.PENDING, is_cancelled=False).select_related(
            "user",
            "practice__subject__department",
            "practice__employer",
        )

        # CR-ARCH-3: Non-admin professors see only applications from their own department
        from users.models import ProfessorUser

        if not user.is_superuser and isinstance(user, ProfessorUser):
            from users.services import get_user_department_ids

            dept_ids = get_user_department_ids(user)
            if dept_ids:
                qs = qs.filter(practice__subject__department_id__in=dept_ids)

        return qs


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
            StudentPractice.objects.filter(filters, approval_status=ApprovalStatus.PENDING, is_cancelled=False)
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

    permission_classes = [IsAuthenticated, IsStagTeacher | IsGarantPraxe | IsAdminUser]
    serializer_class = ListStudentPracticeSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Tohle má být probíhajících praxí po prokliknutí na specifickou praxi
        user = self.request.user
        practice_id = self.kwargs.get("practice_id")

        if not practice_id:
            raise ValidationError({"error": "practice_id is required"})

        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            raise NotFound({"error": "Practice not found"})

        # Filter student practices by practice_id with select_related for optimization
        qs = (
            StudentPractice.objects.filter(practice=practice)
            .select_related(
                "user",
                "practice__subject__department",
                "practice__employer",
            )
            .all()
        )

        # Department scope for non-admin professors
        from users.models import ProfessorUser

        if not user.is_superuser and isinstance(user, ProfessorUser):
            from users.services import get_user_department_ids

            dept_ids = get_user_department_ids(user)
            if dept_ids:
                qs = qs.filter(practice__subject__department_id__in=dept_ids)

        return qs


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
            is_cancelled=False,
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
        IsPracticeOrganizationOwner | IsSubjectTeacherOrHeadForPractice | IsAdminUser,
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
            student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)
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
            raise


class StudentPracticeUploadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = ("document",)

    def validate_document(self, uploaded_file):
        from django.conf import settings

        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        allowed_exts = ("doc", "docx", "pdf", "xlsx")
        if ext not in allowed_exts:
            raise serializers.ValidationError(StudentPracticeMessages.INVALID_EXTENSION)

        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            mb_limit = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise serializers.ValidationError(StudentPracticeMessages.FILE_TOO_LARGE.format(size=mb_limit))

        if ext == "docx":
            import zipfile

            try:
                uploaded_file.seek(0)
                with zipfile.ZipFile(uploaded_file) as zf:
                    names = zf.namelist()
                    if "[Content_Types].xml" not in names:
                        raise serializers.ValidationError("Invalid .docx file structure.")
                uploaded_file.seek(0)
            except zipfile.BadZipFile:
                raise serializers.ValidationError("File is not a valid .docx archive.")

        allowed_mimes = {
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        content_type = getattr(uploaded_file, "content_type", "")
        if content_type and content_type not in allowed_mimes:
            raise serializers.ValidationError(f"Invalid MIME type: {content_type}")

        return uploaded_file

    def update(self, instance, validated_data):
        from student_practices.models import DocumentStatus

        if instance.document:
            instance.document.delete(save=False)

        file = validated_data["document"]
        sp = getattr(instance, "student_practice", None)
        user_id = getattr(getattr(sp, "user", None), "user_id", None) or random.randint(0, 99999999)
        file.name = DocumentHelper.create_name_for_document(instance.document_type, user_id, file.name)
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
        IsSubjectTeacherOrHeadForPractice | IsAdminUser,
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

            # Verify document exists (get_object_or_404 raises 404 if missing)
            get_object_or_404(UploadedDocument, document_id=document_id)

            document = StudentPracticeService.process_document_review(
                user=request.user,
                document_id=document_id,
                status_val=int(status_val),
                review_note=review_note,
            )
            serializer = DocumentReviewSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except PermissionDenied:
            raise  # Let DRF return 403, not 500
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Chyba při recenzi dokumentu")
            raise


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
        import os

        document = get_object_or_404(UploadedDocument, pk=document_id)
        self.check_object_permissions(request, document)

        file_obj = request.FILES.get("document") or request.FILES.get("file")
        if file_obj:
            # Max 10 MB limit check (Item 3.7)
            if file_obj.size > 10 * 1024 * 1024:
                return Response(
                    {"detail": "Velikost souboru nesmí přesáhnout 10 MB."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extension and MIME validation
            ext = os.path.splitext(file_obj.name)[1].lower()
            if ext not in [".pdf", ".docx", ".doc", ".xlsx", ".png", ".jpg", ".jpeg"]:
                return Response(
                    {"detail": "Nepovolený typ souboru. Povolené formáty jsou PDF, DOCX, XLSX, PNG, JPG."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Filename sanitization against path traversal
            safe_name = os.path.basename(file_obj.name).replace("..", "").replace("/", "").replace("\\", "")
            file_obj.name = safe_name

            # late_submission flag: pokud je SP v ENDED a nahrává se po end_date
            sp = document.student_practice
            if sp and sp.workflow_state == StudentPracticeWorkflowState.ENDED:
                from django.utils import timezone

                if sp.end_date and timezone.now().date() > sp.end_date:
                    document.late_submission = True

        serializer = StudentPracticeUploadDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        EmailService.notify_professors_document_upload(document)

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
    """
    Returns detailed information about a specific StudentPractice.

    Ref: CR-ARCH-2 — added IsStudentPracticeAccessible permission to prevent
    any authenticated user from viewing another student's personal data,
    documents, and evaluations (IDOR vulnerability).
    """

    permission_classes = [IsAuthenticated, IsStudentPracticeAccessible]

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
                "practice__contact_user",
                "contract_document",
                "content_document",
                "feedback_document",
            ),
            pk=student_practice_id,
        )
        # CR-ARCH-2: enforce object-level permission (student owner, professor, admin, etc.)
        self.check_object_permissions(request, student_practice)

        serializer = StudentPracticeCardSerializer(student_practice, context={"request": request})

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=student_practice.student_practice_id,
            description=f"Zobrazení karty přihlášky ID {student_practice.student_practice_id}",
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


# ========================================================================
# WP4 — State Machine Endpoints pro StudentPractice
# ========================================================================


class TransitionStudentPracticeView(APIView):
    """
    POST /api/student-practices/{student_practice_id}/transition/
    Provede přechod stavu studentské praxe podle state machine.
    Permissions: IsStagTeacher or IsGarantPraxe or IsAdminUser
    """

    permission_classes = [
        IsAuthenticated,
        IsNotCancelled,
        IsStagTeacher | IsGarantPraxe | IsAdminUser | IsStagStudent | IsOrganizationUser,
    ]

    @extend_schema(
        summary="Transition student practice workflow state",
        description="Provede přechod stavu studentské praxe podle definovaného state machine.",
        tags=["Student Practices"],
        request=TransitionStudentPracticeSerializer,
        responses={200: ListStudentPracticeSerializer},
    )
    def post(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, student_practice)
        serializer = TransitionStudentPracticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from student_practices.models import StudentPracticeWorkflowState

        target_state = StudentPracticeWorkflowState(serializer.validated_data["target_state"])
        reason = serializer.validated_data.get("reason", "")

        try:
            from student_practices.services import StudentPracticeService

            sp = StudentPracticeService.transition_student_practice_state(
                sp=student_practice,
                target_state=target_state,
                actor=request.user,
                reason=reason,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ListStudentPracticeSerializer(sp, context={"request": request}).data)


class WithdrawStudentPracticeView(APIView):
    """
    POST /api/student-practices/{student_practice_id}/withdraw/
    Student stáhne svou žádost (pouze ve stavu APPLIED nebo PRELIMINARY_APPROVED).
    Stav se změní na REJECTED.
    """

    permission_classes = [IsAuthenticated, IsStagStudent, IsStudentOwner]

    @extend_schema(
        summary="Withdraw a student application",
        description=(
            "Student stáhne svou žádost o praxi. Povoleno pouze ve stavu APPLIED nebo PRELIMINARY_APPROVED. " "Stav se změní na REJECTED."
        ),
        tags=["Student Practices"],
        responses={200: ListStudentPracticeSerializer},
    )
    def post(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)

        # Object-level permission: only the student-owner can withdraw
        self.check_object_permissions(request, sp)

        if sp.is_cancelled:
            return Response(
                {"detail": StudentPracticeMessages.CANCELLED_CANNOT_MODIFY},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only APPLIED or PRELIMINARY_APPROVED
        allowed_states = (
            StudentPracticeWorkflowState.APPLIED,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
        )
        if sp.workflow_state not in allowed_states:
            return Response(
                {"detail": "Žádost lze stáhnout pouze ve stavu APPLIED nebo PRELIMINARY_APPROVED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from student_practices.services import withdraw_student_practice

            sp = withdraw_student_practice(sp=sp, actor=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ListStudentPracticeSerializer(sp, context={"request": request}).data)


class CancelStudentPracticeView(APIView):
    """
    POST /api/student-practices/{student_practice_id}/cancel/
    Stornuje studentskou praxi.
    Permissions: CanCancelStudentPractice
    """

    permission_classes = [IsAuthenticated, IsNotCancelled, CanCancelStudentPractice]

    @extend_schema(
        summary="Cancel a student practice",
        description="Stornuje studentskou praxi a zaznamená důvod storna.",
        tags=["Student Practices"],
        request=CancelStudentPracticeSerializer,
        responses={200: ListStudentPracticeSerializer},
    )
    def post(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, student_practice)
        serializer = CancelStudentPracticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data["reason"]
        try:
            from student_practices.services import cancel_student_practice

            sp = cancel_student_practice(sp=student_practice, actor=request.user, reason=reason)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ListStudentPracticeSerializer(sp, context={"request": request}).data)


# ===================================================================
# WP7: Document generation views (contract, content, report, feedback)
# ===================================================================


class StudentPracticeContractDownloadView(APIView):
    """
    Generates and downloads a Czech internship contract (.docx)
    for the given StudentPractice.
    """

    permission_classes = [IsAuthenticated, IsNotCancelled, IsStudentPracticeAccessible]

    @extend_schema(
        summary="Download generated contract",
        description="Generates a Czech internship contract (.docx) from STAG data + template.",
        tags=["Documents"],
        parameters=[
            OpenApiParameter(
                name="student_practice_id",
                location=OpenApiParameter.PATH,
                type=int,
                description="StudentPractice ID",
            ),
        ],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Generated .docx file"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="StudentPractice not found"),
        },
    )
    def get(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, sp)

        from student_practices.services import generate_contract

        buffer = generate_contract(sp)
        filename = f"smlouva_{sp.student_practice_id}.docx"

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Vygenerována smlouva pro praxi ID {sp.student_practice_id}",
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class StudentPracticeContentDownloadView(APIView):
    """Generates and downloads a work content description (Pracovní náplň)."""

    permission_classes = [IsAuthenticated, IsNotCancelled, IsStudentPracticeAccessible]

    @extend_schema(
        summary="Download work content description",
        description="Generates a Pracovní náplň (.docx) document.",
        tags=["Documents"],
        parameters=[
            OpenApiParameter(name="student_practice_id", location=OpenApiParameter.PATH, type=int),
        ],
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY), 403: OpenApiResponse(), 404: OpenApiResponse()},
    )
    def get(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, sp)

        from student_practices.services import generate_content_document

        buffer = generate_content_document(sp)
        filename = f"napln_prace_{sp.student_practice_id}.docx"

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Vygenerována pracovní náplň pro praxi ID {sp.student_practice_id}",
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class StudentPracticeReportDownloadView(APIView):
    """Generates and downloads a practice report/log (Výkaz odborné praxe)."""

    permission_classes = [IsAuthenticated, IsNotCancelled, IsStudentPracticeAccessible]

    @extend_schema(
        summary="Download practice report/log",
        description="Generates a Výkaz odborné praxe (.docx) document.",
        tags=["Documents"],
        parameters=[
            OpenApiParameter(name="student_practice_id", location=OpenApiParameter.PATH, type=int),
        ],
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY), 403: OpenApiResponse(), 404: OpenApiResponse()},
    )
    def get(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, sp)

        from student_practices.services import generate_report

        buffer = generate_report(sp)
        filename = f"vykaz_{sp.student_practice_id}.docx"

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Vygenerován výkaz praxe pro praxi ID {sp.student_practice_id}",
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class StudentPracticeFeedbackDownloadView(APIView):
    """Generates and downloads a practice evaluation form (Hodnocení odborné praxe)."""

    permission_classes = [IsAuthenticated, IsNotCancelled, IsStudentPracticeAccessible]

    @extend_schema(
        summary="Download evaluation form",
        description="Generates a Hodnocení odborné praxe (.docx) document.",
        tags=["Documents"],
        parameters=[
            OpenApiParameter(name="student_practice_id", location=OpenApiParameter.PATH, type=int),
        ],
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY), 403: OpenApiResponse(), 404: OpenApiResponse()},
    )
    def get(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, sp)

        from student_practices.services import generate_feedback_form

        buffer = generate_feedback_form(sp)
        filename = f"hodnoceni_{sp.student_practice_id}.docx"

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Vygenerován formulář hodnocení pro praxi ID {sp.student_practice_id}",
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ReapplyToPracticeView(APIView):
    """Allows a student to re-apply to a practice after their previous application was rejected or cancelled."""

    permission_classes = [IsAuthenticated, IsStagStudent]

    @extend_schema(
        summary="Re-apply to practice",
        description="Creates a new student practice application after a previous one was rejected or cancelled.",
        tags=["Applications"],
        parameters=[OpenApiParameter(name="practice_id", location=OpenApiParameter.PATH, type=int)],
        request=None,
        responses={
            201: StudentPracticeCardSerializer,
            400: OpenApiResponse(description="Validation error (capacity, duplicate, state)"),
            403: OpenApiResponse(),
            404: OpenApiResponse(),
        },
    )
    def post(self, request, practice_id):
        get_object_or_404(Practice, pk=practice_id)
        student = request.user
        try:
            sp = StudentPracticeService.reapply_to_practice(student, practice_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.APPLY,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Student znovu požádal o praxi ID {practice_id} (nové SP ID {sp.student_practice_id})",
        )

        serializer = StudentPracticeCardSerializer(sp, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EvaluationViewSet(ModelViewSet):
    """
    API ViewSet for mentor evaluations (Item 2.1 & 2.12).
    """

    queryset = Evaluation.objects.select_related("student_practice", "evaluated_by")
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        from django.core.files.base import ContentFile

        from student_practices.pdf_service import PDFEvaluationProtocolGenerator

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sp_id = serializer.validated_data.get("student_practice_id")
        sp = get_object_or_404(StudentPractice, pk=sp_id)

        if sp.workflow_state != StudentPracticeWorkflowState.ENDED:
            return Response(
                {"detail": "Evaluaci lze podat pouze u praxe ve stavu ENDED."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if Evaluation.objects.filter(student_practice=sp).exists():
            return Response(
                {"detail": "Evaluace pro tuto praxi již byla odeslána."},
                status=status.HTTP_409_CONFLICT,
            )

        evaluation = serializer.save(evaluated_by=request.user)

        # Auto-generate PDF protocol (RF-10 / Item 2.12)
        try:
            pdf_bytes = PDFEvaluationProtocolGenerator.generate_pdf(evaluation)
            filename = f"eval_protocol_sp_{sp.student_practice_id}.pdf"
            evaluation.pdf_protokol.save(filename, ContentFile(pdf_bytes), save=True)
        except Exception as e:
            logger.error(f"Failed to generate evaluation PDF protocol: {e}")

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.CREATE,
            object_type="Evaluation",
            object_id=evaluation.evaluation_id,
            description=f"Mentorská evaluace vytvořena pro SP #{sp.student_practice_id}",
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StudentPracticeHistoryView(APIView):
    """
    GET /api/student-practices/{student_practice_id}/history/
    Vrací chronologický seznam ActionLog záznamů pro danou StudentPractice.
    Přístup: student (owner), profesor, garant, organizace, admin.
    """

    permission_classes = [IsAuthenticated, IsStudentPracticeAccessible]

    @extend_schema(
        summary="Get ActionLog history for a student practice",
        description="Returns a chronological list of ActionLog entries for the given StudentPractice.",
        tags=["Student Practices"],
        responses={200: ActionLogSerializer(many=True)},
    )
    def get(self, request, student_practice_id):
        sp = get_object_or_404(StudentPractice, pk=student_practice_id)
        self.check_object_permissions(request, sp)

        logs = (
            ActionLog.objects.filter(
                object_type="StudentPractice",
                object_id=sp.student_practice_id,
            )
            .select_related("user")
            .order_by("-action_date")
        )

        serializer = ActionLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConfirmContractView(APIView):
    """
    Confirms contract receipt and updates contract status (Item 2.7).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sp = get_object_or_404(StudentPractice, pk=pk)
        sp.contract_received_date = timezone.now()
        sp.workflow_state = StudentPracticeWorkflowState.CONTRACTED
        sp.save()

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.APPROVE,
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            description=f"Potvrzení přijetí smlouvy u SP #{sp.student_practice_id}",
        )

        return Response(
            {"detail": "Přijetí smlouvy bylo úspěšně potvrzeno.", "contract_received_date": sp.contract_received_date},
            status=status.HTTP_200_OK,
        )
