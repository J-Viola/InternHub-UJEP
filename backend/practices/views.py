import logging
from datetime import date

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.views import StandardResultsSetPagination
from department.models import Department
from practices.filters import PracticeFilter
from practices.messages import PracticeMessages
from practices.models import Practice, ProgressStatus
from practices.serializers import (
    EndDateRequestSerializer,
    EndDateResponseSerializer,
    OrganizationPracticeSerializer,
    PracticeApprovalSerializer,
    PracticeApprovalStatusSerializer,
    PracticeSerializer,
    RunningPracticeSerializer,
)
from student_practices.serializers import ListStudentPracticeSerializer
from practices.services import PracticeService
from practices.utils import calculate_end_date
from users.models import ApprovalStatus, ProfessorUser, StagRoleEnum, StudentUser
from users.permissions import IsOrganizationOwner, IsOrganizationUser, IsStagTeacher

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# 1. StudentPracticeViewSet – Prohlížení a přihlašování (Studenti)
# -------------------------------------------------------------
@extend_schema(tags=["Practices - Student"])
class StudentPracticeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for students to view active practices and apply for them.
    """

    serializer_class = PracticeSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PracticeFilter
    search_fields = ["title", "description", "employer__company_name"]
    ordering_fields = ["start_date", "end_date", "title", "practice_id"]

    def get_queryset(self):
        return (
            Practice.objects.filter(is_active=True)
            .select_related("employer")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(
                        student_practices__approval_status=ApprovalStatus.APPROVED
                    ),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
        )

    @extend_schema(
        summary="Get user's practices and invitations", tags=["Practices - Student"]
    )
    @action(detail=False, methods=["get"])
    def get_practice_user_relations(self, request):
        user = request.user
        if not user.pk:
            return Response(
                {"detail": PracticeMessages.USER_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = PracticeService.get_user_practices_and_invitations(user)
        return Response(result)

    @extend_schema(
        summary="Apply for a practice (student)", tags=["Practices - Student"]
    )
    @action(detail=False, methods=["post"])
    def apply(self, request):
        user = request.user
        practice_id = request.data.get("practice")
        if not practice_id:
            return Response(
                {"detail": PracticeMessages.MISSING_PRACTICE_ID},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = PracticeService.apply_student_practice(user, practice_id)
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Toggle favorite practice", tags=["Practices - Student"])
    @action(detail=True, methods=["post"])
    def toggle_favorite(self, request, pk=None):
        user = request.user
        if not hasattr(user, "favorite_practices"):
            return Response(
                {"detail": "User cannot have favorite practices"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        practice = self.get_object()
        if user.favorite_practices.filter(pk=practice.pk).exists():
            user.favorite_practices.remove(practice)
            return Response({"detail": "REMOVED_FROM_FAVORITES", "is_favorite": False})
        else:
            user.favorite_practices.add(practice)
            return Response({"detail": "ADDED_TO_FAVORITES", "is_favorite": True})

    @extend_schema(summary="Get upcoming practices", tags=["Practices - Student"])
    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        today = date.today()
        upcoming_practices = (
            self.get_queryset().filter(start_date__gte=today).order_by("start_date")
        )
        page = self.paginate_queryset(upcoming_practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(upcoming_practices, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get practices by subject", tags=["Practices - Student"])
    @action(detail=False, methods=["get"])
    def by_subject(self, request):
        subj_id = request.query_params.get("subject_id")
        if not subj_id:
            return Response(
                {"detail": PracticeMessages.MISSING_SUBJECT_ID},
                status=status.HTTP_400_BAD_REQUEST,
            )
        practices = (
            self.get_queryset().filter(subject_id=subj_id).order_by("start_date")
        )
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# 2. EmployerPracticeViewSet – Správa firemních nabídek (Firmy)
# -------------------------------------------------------------
@extend_schema(tags=["Practices - Employer"])
class EmployerPracticeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for employers to manage their own practices.
    """

    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PracticeSerializer
        return OrganizationPracticeSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsOrganizationOwner()]
        return [permissions.IsAuthenticated(), IsOrganizationUser()]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "employer_profile") or not user.employer_profile:
            return Practice.objects.none()

        # For list action, filter by employer
        if self.action == "list":
            return PracticeService.get_organization_practices_queryset(
                user.employer_profile
            ).annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(
                        student_practices__approval_status=ApprovalStatus.APPROVED
                    ),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )

        # For other actions (retrieve, update, delete), return all to allow 403 instead of 404
        return Practice.objects.all()

    @extend_schema(summary="Create a new practice")
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        data["employer_id"] = user.employer_profile.employer_id
        if user.employer_profile.logo:
            data["image_base64"] = PracticeService.encode_logo_to_base64(
                user.employer_profile.logo
            )

        # Set critical defaults to avoid IntegrityErrors
        data.setdefault("approval_status", ApprovalStatus.PENDING.value)
        data.setdefault("progress_status", ProgressStatus.NOT_STARTED.value)

        if "coefficient" not in data or data["coefficient"] is None:
            data["coefficient"] = 1.0

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------
# 3. StaffPracticeViewSet – Schvalování a přehledy (Učitelé/Admini)
# -------------------------------------------------------------
@extend_schema(tags=["Practices - Staff"])
class StaffPracticeViewSet(viewsets.GenericViewSet):
    """
    ViewSet for teachers and department heads to manage and approve practices.
    """

    permission_classes = [IsAuthenticated, IsStagTeacher]
    pagination_class = StandardResultsSetPagination

    @extend_schema(summary="List practices waiting for approval")
    @action(detail=False, methods=["get"], serializer_class=PracticeApprovalSerializer)
    def pending(self, request):
        dept_ids = (
            Department.objects.filter(professor_users=request.user)
            .values_list("department_id", flat=True)
            .distinct()
        )
        practices = (
            Practice.objects.filter(
                subject__department_id__in=dept_ids,
                approval_status=ApprovalStatus.PENDING,
            )
            .select_related("subject__department", "employer")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Change approval status of a practice")
    @action(
        detail=True, methods=["post"], serializer_class=PracticeApprovalStatusSerializer
    )
    def approve(self, request, pk=None):
        practice_obj = get_object_or_404(Practice, pk=pk)
        if practice_obj.approval_status != ApprovalStatus.PENDING:
            return Response(
                {"detail": PracticeMessages.ALREADY_APPROVED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approval_status = ApprovalStatus.get(
            name_or_numeric=serializer.validated_data.get("approval_status")
        )
        practice_obj.approval_status = approval_status
        practice_obj.save()
        return Response(PracticeSerializer(practice_obj).data)

    @extend_schema(summary="Get practices by user department (Approved vs Pending)")
    @action(detail=False, methods=["get"])
    def department_overview(self, request):
        user = request.user
        result = PracticeService.get_practices_by_department(user)
        if result is None:
            return Response(
                {"detail": PracticeMessages.NO_DEPARTMENT},
                status=status.HTTP_404_NOT_FOUND,
            )

        approved = result["approved"]
        to_approve = result["to_approve"]

        approved_data = ListStudentPracticeSerializer(
            approved, many=True, context={"request": request}
        ).data
        to_approve_data = PracticeSerializer(
            to_approve, many=True, context={"request": request}
        ).data
        to_approve_data = PracticeService.enrich_contact_user_info(
            to_approve_data, to_approve
        )

        return Response(
            {
                "approved_practices": approved_data,
                "to_approve_practices": to_approve_data,
            }
        )

    @extend_schema(summary="List running practices for department")
    @action(detail=False, methods=["get"], serializer_class=RunningPracticeSerializer)
    def running(self, request):
        user = request.user
        is_head_of_department = (
            isinstance(user, ProfessorUser)
            and hasattr(user, "stag_role")
            and user.stag_role
            and user.stag_role.role == StagRoleEnum.VK.value
        )

        if is_head_of_department:
            dept_ids = (
                Department.objects.all()
                .values_list("department_id", flat=True)
                .distinct()
            )
        else:
            dept_ids = (
                Department.objects.filter(subjects__user_subjects__user=user)
                .values_list("department_id", flat=True)
                .distinct()
            )

        students = StudentUser.objects.filter(
            user_subjects__subject__department_id__in=dept_ids
        ).distinct()
        practices = (
            Practice.objects.filter(
                student_practices__user__in=students, is_active=True
            )
            .distinct()
            .annotate(
                total_student_count=Count("student_practices"),
                approved_count=Count(
                    "student_practices",
                    filter=Q(
                        student_practices__approval_status=ApprovalStatus.APPROVED
                    ),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
        )
        page = self.paginate_queryset(practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(practices, many=True).data)


# -------------------------------------------------------------
# Utils & Admin
# -------------------------------------------------------------
class GetEndDateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Calculate end date of practice", tags=["Utils"])
    def post(self, request, *args, **kwargs):
        serializer = EndDateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        end_date = calculate_end_date(
            serializer.validated_data["start_date"],
            serializer.validated_data["coefficient"],
        )
        return Response(
            EndDateResponseSerializer({"end_date": end_date}).data,
            status=status.HTTP_200_OK,
        )


class AdminPracticesListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = OrganizationPracticeSerializer

    def get_queryset(self):
        return (
            Practice.objects.all()
            .select_related("subject", "subject__department", "contact_user")
            .prefetch_related("student_practices")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(
                        student_practices__approval_status=ApprovalStatus.APPROVED
                    ),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(
            {
                "approved_practices": self.get_serializer(
                    queryset.filter(approval_status=ApprovalStatus.APPROVED), many=True
                ).data,
                "to_approve_practices": self.get_serializer(
                    queryset.filter(approval_status=ApprovalStatus.PENDING), many=True
                ).data,
            }
        )
