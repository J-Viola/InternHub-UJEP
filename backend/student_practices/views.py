import datetime
from datetime import date

from api.models import (
    ApprovalStatus,
    DocumentHelper,
    EmployerInvitation,
    EmployerInvitationStatus,
    Practice,
    ProfessorUser,
    ProgressStatus,
    StudentPractice,
    StudentUser,
    UploadedDocument,
    UserSubjectType,
    OrganizationUser,
)
from django.db import transaction
from django.http import FileResponse, JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import EmployerInvitationApprovalSerializer, ListStudentPracticeSerializer, StudentPracticeCardSerializer


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

        try:
            # Najdi invitation
            invitation = EmployerInvitation.objects.get(invitation_id=invitation_id, user=request.user)
        except EmployerInvitation.DoesNotExist:
            return Response({"detail": "Pozvánka nebyla nalezena nebo k ní nemáte přístup."}, status=status.HTTP_404_NOT_FOUND)

        # Zkontroluj, že invitation je ve stavu PENDING
        if invitation.status != EmployerInvitationStatus.PENDING:
            return Response({"detail": "Pozvánka již byla zpracována."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if action == "accept":
                # Změň status invitation na ACCEPTED
                invitation.status = EmployerInvitationStatus.ACCEPTED
                invitation.save()

                # Vytvoř StudentPractice záznam
                student_practice = StudentPractice.objects.create(
                    user=request.user,
                    practice=invitation.practice,
                    application_date=date.today(),
                    approval_status=ApprovalStatus.APPROVED,  # Automaticky schváleno
                    progress_status=ProgressStatus.IN_PROGRESS,  # Probíhá
                    hours_completed=0,
                    year=date.today().year,
                )

                return Response(
                    {"detail": "Pozvánka byla přijata a praxe byla zahájena.", "student_practice_id": student_practice.student_practice_id},
                    status=status.HTTP_200_OK,
                )

            elif action == "reject":
                invitation.status = EmployerInvitationStatus.REJECTED
                invitation.save()

                return Response({"detail": "Pozvánka byla zamítnuta."}, status=status.HTTP_200_OK)

        return Response({"detail": "Neplatná akce."}, status=status.HTTP_400_BAD_REQUEST)


class StudentPracticeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ListStudentPracticeSerializer

    def get_queryset(self):
        # Tohle má být probíhajících praxí po prokliknutí na specifickou praxi
        practice_id = self.kwargs.get("practice_id")

        if not practice_id:
            return JsonResponse({"error": "practice_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            return JsonResponse({"error": "Practice not found"}, status=status.HTTP_404_NOT_FOUND)

        # Filter student practices by practice_id
        return StudentPractice.objects.filter(practice=practice).all()


class OrganizationApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Zjisti employer_profile id z přihlášeného uživatele (OrganizationUser)
        employer_profile = getattr(user, "employer_profile", None)
        if not employer_profile:
            return Response({"detail": "Uživatel není přiřazen k žádné organizaci."}, status=status.HTTP_400_BAD_REQUEST)

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
        instance.uploaded_at = datetime.datetime.now()
        instance.save()
        return instance


class HasDocumentAccessMixin:
    def _has_document_access(self, user, document):
        if user.is_superuser:
            return True
        if isinstance(user, StudentUser):
            return document.student_practice.user == user
        elif isinstance(user, ProfessorUser):
            user_subjects = document.student_practice.practice.subject.user_subjects
            is_professor_for_subject = user_subjects.filter(user=user, role=UserSubjectType.Professor).exists()
            if is_professor_for_subject:
                return True
        elif isinstance(user, OrganizationUser):
            # Organizační uživatel má přístup k dokumentům praxí své organizace
            return document.student_practice.practice.employer == user.employer_profile
        return False


class StudentPracticeUploadDocumentView(APIView, HasDocumentAccessMixin):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Upload a document for a student practice",
        description="Uploads a file and attaches it to the specified StudentPractice record.",
        parameters=[
            OpenApiParameter(name="document_id", location=OpenApiParameter.PATH, type=int, description="ID of the student practice"),
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

        if not self._has_document_access(request.user, document):
            return Response({"detail": "Nemáte oprávnění nahrát dokument k této praxi."}, status=status.HTTP_403_FORBIDDEN)

        serializer = StudentPracticeUploadDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Dokument byl úspěšně nahrán."}, status=status.HTTP_201_CREATED)


class StudentPracticeDownloadDocumentView(APIView, HasDocumentAccessMixin):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Download a document",
        description="Streams the file associated with the given UploadedDocument ID.",
        parameters=[
            OpenApiParameter(name="document_id", location=OpenApiParameter.PATH, type=int, description="ID of the uploaded document"),
        ],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Binary stream of the requested file"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="UploadedDocument not found"),
        },
    )
    def get(self, request, document_id):
        document = get_object_or_404(UploadedDocument, pk=document_id)

        if not self._has_document_access(request.user, document):
            return Response({"detail": "Nemáte oprávnění stáhnout dokument k této praxi."}, status=status.HTTP_403_FORBIDDEN)

        file_handle = document.document.open("rb")
        return FileResponse(file_handle, as_attachment=True, filename=document.document.name)


class StudentPracticeCardView(APIView):

    @extend_schema(
        summary="Get student practice card",
        description="Returns detailed information about a specific student practice.",
        parameters=[
            OpenApiParameter(
                name="student_practice_id", location=OpenApiParameter.PATH, type=int, description="ID of the student practice"
            ),
        ],
        responses={
            200: OpenApiResponse(response=StudentPracticeCardSerializer, description="Student practice details"),
            404: OpenApiResponse(description="StudentPractice not found"),
        },
    )
    def get(self, request, student_practice_id):
        student_practice = get_object_or_404(StudentPractice, pk=student_practice_id)

        serializer = StudentPracticeCardSerializer(student_practice)
        return Response(serializer.data, status=status.HTTP_200_OK)
