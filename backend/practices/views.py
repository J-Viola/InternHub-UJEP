import logging
from datetime import date

from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from notifications.models import NotificationType
from notifications.services import EmailService, NotificationService
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
from practices.models import (
    ApplicationClosureReason,
    Practice,
    PracticeWorkflowState,
    ProgressStatus,
)
from practices.serializers import (
    CancelPracticeSerializer,
    CloseApplicationsSerializer,
    EndDateRequestSerializer,
    EndDateResponseSerializer,
    ExternalPracticeSerializer,
    OrganizationPracticeSerializer,
    PracticeApprovalSerializer,
    PracticeApprovalStatusSerializer,
    PracticeSerializer,
    RunningPracticeSerializer,
    TransitionPracticeSerializer,
)
from practices.services import PracticeService
from practices.utils import calculate_end_date
from student_practices.serializers import ListStudentPracticeSerializer
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ApprovalStatus, ProfessorUser, StagRoleEnum, StudentUser
from users.permissions import (
    CanCancelPractice,
    IsAdminUser,
    IsApprovedOrganization,
    IsGarantPraxe,
    IsNotCancelled,
    IsOrganizationOrReadOnly,
    IsOrganizationOwner,
    IsStagTeacher,
)

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
        # Katalog zobrazuje pouze „Aktivní" nabídky — schválený obsah a otevřený sběr
        # přihlášek; stornované nabídky se nezobrazují.
        qs = (
            Practice.objects.filter(
                is_active=True,
                workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
                is_cancelled=False,
            )
            .select_related("employer", "subject", "subject__department", "contact_user")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.APPROVED),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
        )

        if self.request.user.is_authenticated:
            from student_practices.models import StudentPractice

            qs = qs.prefetch_related(
                Prefetch(
                    "student_practices",
                    queryset=StudentPractice.objects.filter(user_id=self.request.user.id),
                    to_attr="_current_user_practices",
                )
            )

        return qs

    @extend_schema(summary="Get user's practices and invitations", tags=["Practices - Student"])
    @action(detail=False, methods=["get"])
    def get_practice_user_relations(self, request):
        user = request.user
        if not user.pk:
            return Response(
                {"detail": PracticeMessages.USER_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = PracticeService.get_user_practices_and_invitations(user)

        ActionLogService.log(
            user=user,
            action_type=ActionLogType.VIEW,
            object_type="StudentPractice",
            description=f"Student {user.email} zobrazení vlastních praxí a pozvánek",
        )

        return Response(result)

    @extend_schema(summary="Apply for a practice (student)", tags=["Practices - Student"])
    @action(detail=False, methods=["post"])
    def apply(self, request):
        user = request.user

        # Only students can apply
        if not isinstance(user, StudentUser):
            return Response(
                {"detail": "Only students can apply for practices"},
                status=status.HTTP_403_FORBIDDEN,
            )

        practice_id = request.data.get("practice")
        if not practice_id:
            return Response(
                {"detail": PracticeMessages.MISSING_PRACTICE_ID},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = PracticeService.apply_student_practice(user, practice_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
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

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.TOGGLE_FAVORITE,
                object_type="Practice",
                object_id=practice.pk,
                description=f"Student {user.email} odebral praxi '{practice.title}' z oblíbených",
            )

            return Response({"detail": "REMOVED_FROM_FAVORITES", "is_favorite": False})
        else:
            user.favorite_practices.add(practice)

            ActionLogService.log(
                user=user,
                action_type=ActionLogType.TOGGLE_FAVORITE,
                object_type="Practice",
                object_id=practice.pk,
                description=f"Student {user.email} přidal praxi '{practice.title}' do oblíbených",
            )

            return Response({"detail": "ADDED_TO_FAVORITES", "is_favorite": True})

    @extend_schema(summary="Get upcoming practices", tags=["Practices - Student"])
    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        today = date.today()
        upcoming_practices = self.get_queryset().filter(start_date__gte=today).order_by("start_date")

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            description=f"Student {request.user.email} zobrazení nadcházejících praxí",
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
        practices = self.get_queryset().filter(subject_id=subj_id).order_by("start_date")
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            object_id=instance.pk,
            description=f"Zobrazení detailu praxe '{instance.title}' (ID: {instance.pk})",
        )

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
            # update/delete vyžadují vlastnictví (IsOrganizationOwner)
            # i schválený profil organizace (IsApprovedOrganization → 403
            # EMPLOYER_NOT_APPROVED pro PENDING/REJECTED).
            return [permissions.IsAuthenticated(), IsOrganizationOwner(), IsApprovedOrganization()]
        return [permissions.IsAuthenticated(), IsOrganizationOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "employer_profile") or not user.employer_profile:
            return Practice.objects.none()

        # For list action, filter by employer
        if self.action == "list":
            return PracticeService.get_organization_practices_queryset(user.employer_profile).annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.APPROVED),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )

        # For other actions (retrieve, update, delete), return all to allow 403 instead of 404
        return Practice.objects.all()

    @extend_schema(summary="List organization practices")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Get organization practice detail")
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            object_id=instance.pk,
            description=f"Zaměstnavatel zobrazení detailu nabídky '{instance.title}' (ID: {instance.pk})",
        )

        return Response(serializer.data)

    @extend_schema(summary="Create a new practice")
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        data["employer_id"] = user.employer_profile.employer_id
        if user.employer_profile.logo:
            data["image_base64"] = PracticeService.encode_logo_to_base64(user.employer_profile.logo)

        # Set critical defaults to avoid IntegrityErrors
        data.setdefault("approval_status", ApprovalStatus.PENDING.value)
        data.setdefault("progress_status", ProgressStatus.NOT_STARTED.value)

        # DEPRECATION: coefficient je nyní read-only; Subject.min_hours se používá pro výpočet end_date.
        if "coefficient" in data and data["coefficient"] is not None:
            logger.warning(
                "coefficient field is deprecated and read-only — value ignored. "
                "Use Subject.min_hours (default 480) for practice duration.",
            )
            # Remove from data so the read-only serializer field ignores it
            del data["coefficient"]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # 3.8: Notifikace garantovi při vytvoření inzerátu
        practice = serializer.instance
        if practice and practice.subject and practice.subject.subject_manager:
            garant = practice.subject.subject_manager
            NotificationService.create_notification(
                recipient=garant,
                verb="PRACTICE_CREATED",
                message=f"Byla vytvořena nová nabídka praxe '{practice.title}' organizací "
                f"{practice.employer.company_name if practice.employer else 'externí organizace'}.",
                actor=request.user,
                target=practice,
                notification_type=NotificationType.INFO,
            )
            EmailService._send_email(
                subject="Nová nabídka praxe ke schválení",
                message=(
                    f"Dobrý den,\n\n"
                    f"byla vytvořena nová nabídka praxe '{practice.title}', "
                    f"která čeká na Vaše schválení v systému InternHub.\n\n"
                    f"Tým InternHub"
                ),
                recipient_list=[garant.email],
            )

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.CREATE,
            object_type="Practice",
            object_id=serializer.data.get("practice_id"),
            description=f"Zaměstnavatel vytvořil nabídku praxe: {serializer.data.get('title', '')}",
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Update an organization practice")
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # 2.6: Explicitní blokace — aktivní inzeráty nelze editovat
        blocked_states = [
            PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            PracticeWorkflowState.CLOSED_FOR_APPLICATIONS,
        ]
        if instance.workflow_state in blocked_states:
            return Response(
                {"detail": "Úprava není povolena pro aktivní inzerát."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # 3.6: Blokace editace — pouze PENDING_CONTENT_APPROVAL nebo CONTENT_REJECTED
        if instance.workflow_state not in (
            PracticeWorkflowState.PENDING_CONTENT_APPROVAL,
            PracticeWorkflowState.CONTENT_REJECTED,
        ):
            return Response(
                {"detail": "Nabídku lze editovat pouze ve stavu PENDING_CONTENT_APPROVAL nebo CONTENT_REJECTED."},
                status=status.HTTP_403_FORBIDDEN,
            )
        response = super().update(request, *args, **kwargs)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.UPDATE,
            object_type="Practice",
            object_id=instance.pk,
            description=f"Zaměstnavatel upravil nabídku praxe '{instance.title}' (ID: {instance.pk})",
        )
        return response

    @extend_schema(summary="Partially update an organization practice")
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        # 2.6: Explicitní blokace — aktivní inzeráty nelze editovat
        blocked_states = [
            PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
            PracticeWorkflowState.CLOSED_FOR_APPLICATIONS,
        ]
        if instance.workflow_state in blocked_states:
            return Response(
                {"detail": "Úprava není povolena pro aktivní inzerát."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # 3.6: Blokace editace — pouze PENDING_CONTENT_APPROVAL nebo CONTENT_REJECTED
        if instance.workflow_state not in (
            PracticeWorkflowState.PENDING_CONTENT_APPROVAL,
            PracticeWorkflowState.CONTENT_REJECTED,
        ):
            return Response(
                {"detail": "Nabídku lze editovat pouze ve stavu PENDING_CONTENT_APPROVAL nebo CONTENT_REJECTED."},
                status=status.HTTP_403_FORBIDDEN,
            )
        response = super().partial_update(request, *args, **kwargs)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.UPDATE,
            object_type="Practice",
            object_id=instance.pk,
            description=f"Částečná úprava nabídky praxe '{instance.title}' (ID: {instance.pk})",
        )
        return response

    @extend_schema(summary="Delete an organization practice")
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Block deletion if practice has active (non-cancelled) applications
        if instance.student_practices.filter(is_cancelled=False).exists():
            return Response(
                {"detail": "Cannot delete practice with active applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Soft-delete via service layer for consistent audit trail + notifications
        with transaction.atomic():
            instance = PracticeService.cancel_practice(
                practice=instance,
                actor=request.user,
                reason="Deleted by employer",
            )

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.STORNO,
            object_type="Practice",
            object_id=instance.pk,
            description=f"Smazání nabídky praxe '{instance.title}' (ID: {instance.pk})",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------------------------------------------------
# 3. StaffPracticeViewSet – Schvalování a přehledy (Učitelé/Admini)
# -------------------------------------------------------------
@extend_schema(tags=["Practices - Staff"])
class StaffPracticeViewSet(viewsets.GenericViewSet):
    """
    ViewSet for teachers and department heads to manage and approve practices.
    Admins (OrganizationUser with is_superuser) can also approve practices.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action == "approve":
            return [IsAuthenticated(), (IsStagTeacher | IsAdminUser)()]
        return [IsAuthenticated(), IsStagTeacher()]

    @extend_schema(summary="List practices waiting for approval")
    @action(detail=False, methods=["get"], serializer_class=PracticeApprovalSerializer)
    def pending(self, request):
        dept_ids = Department.objects.filter(professor_users=request.user).values_list("department_id", flat=True).distinct()
        practices = (
            Practice.objects.filter(
                subject__department_id__in=dept_ids,
                approval_status=ApprovalStatus.PENDING,
            )
            .select_related("subject__department", "employer")
            .order_by("-created_at")
        )

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            description=f"Profesor {request.user.email} zobrazení čekajících praxí na schválení",
        )
        page = self.paginate_queryset(practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Change approval status of a practice")
    @action(detail=True, methods=["post"], serializer_class=PracticeApprovalStatusSerializer)
    def approve(self, request, pk=None):
        practice_obj = get_object_or_404(Practice, pk=pk)

        if not request.user.is_superuser:
            dept_ids = Department.objects.filter(professor_users=request.user).values_list("department_id", flat=True).distinct()
            if practice_obj.subject and practice_obj.subject.department_id not in dept_ids:
                return Response(
                    {"detail": "You are not authorized to approve practices from this department."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if practice_obj.approval_status != ApprovalStatus.PENDING:
            return Response(
                {"detail": PracticeMessages.ALREADY_APPROVED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            approval_status = ApprovalStatus.get(name_or_numeric=serializer.validated_data.get("approval_status"))
            practice_obj.approval_status = approval_status
            practice_obj.save()

            # Also update workflow_state to keep state machine consistent
            new_workflow_state = (
                PracticeWorkflowState.CONTENT_APPROVED
                if approval_status == ApprovalStatus.APPROVED
                else PracticeWorkflowState.CONTENT_REJECTED
            )
            practice_obj = PracticeService.transition_practice_state(
                practice_obj,
                new_workflow_state,
                request.user,
                reason="Schváleno přes starý approve endpoint",
            )

            if approval_status == ApprovalStatus.APPROVED:
                # FE-004 / SRS oracle (Tests/SRS/extracted/analysis.txt:2248): „Garant může
                # inzerát schválit (přechod do stavu „Aktivní", kdy je viditelný pro studenty)".
                # Schválení garantem JE aktivace — řetěz CONTENT_APPROVED → OPEN_FOR_APPLICATIONS
                # se provádí automaticky v téže akci (žádný manuální „otevřít sběr" krok).
                # Mapa PRACTICE_TRANSITIONS ani sanovaný endpoint /transition/ se nemění.
                practice_obj = PracticeService.transition_practice_state(
                    practice_obj,
                    PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
                    request.user,
                    reason="Automatická aktivace po schválení obsahu (SRS analysis.txt:2248)",
                )

        EmailService.notify_org_practice_status(practice_obj)

        status_name = "schválena" if approval_status == ApprovalStatus.APPROVED else "zamítnuta"
        action_type = ActionLogType.APPROVE if approval_status == ApprovalStatus.APPROVED else ActionLogType.REJECT

        ActionLogService.log(
            user=request.user,
            action_type=action_type,
            object_type="Practice",
            object_id=practice_obj.pk,
            description=f"Praxe '{practice_obj.title}' (ID: {practice_obj.pk}) {status_name} uživatelem {request.user.email}",
        )

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
        active_offers = result["active"]

        approved_data = ListStudentPracticeSerializer(approved, many=True, context={"request": request}).data
        to_approve_data = PracticeSerializer(to_approve, many=True, context={"request": request}).data
        to_approve_data = PracticeService.enrich_contact_user_info(to_approve_data, to_approve)

        # FE-004: aktivní (schválené) nabídky zůstávají v přehledu viditelné —
        # viz analysis.txt:2248 (schválení = přechod do stavu „Aktivní").
        active_offers_data = PracticeSerializer(active_offers, many=True, context={"request": request}).data
        active_offers_data = PracticeService.enrich_contact_user_info(active_offers_data, active_offers)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            description=f"Profesor {request.user.email} zobrazení přehledu katedry",
        )

        return Response(
            {
                "approved_practices": approved_data,
                "to_approve_practices": to_approve_data,
                "active_offers": active_offers_data,
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
            and user.stag_role.role.lower() == StagRoleEnum.VK
        )

        if is_head_of_department:
            dept_ids = Department.objects.all().values_list("department_id", flat=True).distinct()
        else:
            dept_ids = Department.objects.filter(subjects__user_subjects__user=user).values_list("department_id", flat=True).distinct()

        students = StudentUser.objects.filter(user_subjects__subject__department_id__in=dept_ids).distinct()
        practices = (
            Practice.objects.filter(student_practices__user__in=students, is_active=True)
            .select_related("subject", "contact_user")
            .distinct()
            .annotate(
                total_student_count=Count("student_practices"),
                approved_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.APPROVED),
                ),
                pending_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.PENDING),
                ),
            )
        )

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.VIEW,
            object_type="Practice",
            description=f"Profesor {request.user.email} zobrazení běžících praxí",
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
            start_date=serializer.validated_data["start_date"],
            coefficient=serializer.validated_data.get("coefficient"),
            min_hours=serializer.validated_data.get("min_hours"),
        )
        return Response(
            EndDateResponseSerializer({"end_date": end_date}).data,
            status=status.HTTP_200_OK,
        )


class AdminPracticesListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = OrganizationPracticeSerializer

    @extend_schema(
        summary="List all practices grouped by status (Admin)",
        tags=["Practices - Admin"],
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Practice.objects.all()
            .select_related("subject", "subject__department", "contact_user")
            .prefetch_related("student_practices")
            .annotate(
                approved_count=Count(
                    "student_practices",
                    filter=Q(student_practices__approval_status=ApprovalStatus.APPROVED),
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
        # For approved practices, return StudentPractice objects so the frontend
        # can display workflow states, contract status, and navigate to practice cards.
        from student_practices.models import StudentPractice
        from student_practices.serializers import ListStudentPracticeSerializer

        # Evaluate the base queryset once (avoids re-executing filter twice).
        # Materialize both subsets before serialization.
        pending_qs = queryset.filter(approval_status=ApprovalStatus.PENDING)
        approved_ids = list(queryset.filter(approval_status=ApprovalStatus.APPROVED).values_list("practice_id", flat=True))

        approved_student_practices = StudentPractice.objects.filter(practice_id__in=approved_ids, is_cancelled=False).select_related(
            "user", "practice__subject__department", "practice__employer"
        )

        return Response(
            {
                "approved_practices": ListStudentPracticeSerializer(
                    approved_student_practices, many=True, context={"request": request}
                ).data,
                "to_approve_practices": self.get_serializer(pending_qs, many=True).data,
            }
        )


# -------------------------------------------------------------
# 4. State Machine Endpoints — Přechody, storno, uzávěrka
# -------------------------------------------------------------


class TransitionPracticeView(APIView):
    """
    POST /api/practices/{pk}/transition/
    Provede přechod stavu nabídky podle state machine.
    Permissions: IsStagTeacher or IsGarantPraxe or IsAdminUser
    """

    permission_classes = [IsAuthenticated, IsNotCancelled, (IsStagTeacher | IsGarantPraxe | IsAdminUser)]

    @extend_schema(
        summary="Transition practice workflow state",
        description="Provede přechod stavu nabídky praxe podle definovaného state machine.",
        tags=["Practices - Staff"],
        request=TransitionPracticeSerializer,
        responses={200: PracticeSerializer},
    )
    def post(self, request, pk):
        practice = get_object_or_404(Practice, pk=pk)
        self.check_object_permissions(request, practice)
        serializer = TransitionPracticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_state = PracticeWorkflowState(serializer.validated_data["target_state"])
        reason = serializer.validated_data.get("reason", "")

        try:
            practice = PracticeService.transition_practice_state(
                practice=practice,
                target_state=target_state,
                actor=request.user,
                reason=reason,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PracticeSerializer(practice).data)


class CancelPracticeView(APIView):
    """
    POST /api/practices/{pk}/cancel/
    Stornuje nabídku praxe.
    Permissions: CanCancelPractice
    """

    permission_classes = [IsAuthenticated, IsNotCancelled, CanCancelPractice]

    @extend_schema(
        summary="Cancel a practice",
        description="Stornuje nabídku praxe — deaktivuje ji a zaznamená důvod storna.",
        tags=["Practices - Staff"],
        request=CancelPracticeSerializer,
        responses={200: PracticeSerializer},
    )
    def post(self, request, pk):
        practice = get_object_or_404(Practice, pk=pk)
        self.check_object_permissions(request, practice)
        serializer = CancelPracticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data["reason"]
        try:
            practice = PracticeService.cancel_practice(practice=practice, actor=request.user, reason=reason)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PracticeSerializer(practice).data)


class CloseApplicationsView(APIView):
    """
    POST /api/practices/{pk}/close-applications/
    Uzavře sběr přihlášek na nabídku.
    Permissions: IsStagTeacher or IsGarantPraxe or IsAdminUser
    """

    permission_classes = [IsAuthenticated, IsNotCancelled, (IsStagTeacher | IsGarantPraxe | IsAdminUser)]

    @extend_schema(
        summary="Close practice for applications",
        description="Uzavře sběr přihlášek na nabídku praxe (manuálně).",
        tags=["Practices - Staff"],
        request=CloseApplicationsSerializer,
        responses={200: PracticeSerializer},
    )
    def post(self, request, pk):
        practice = get_object_or_404(Practice, pk=pk)
        self.check_object_permissions(request, practice)
        serializer = CloseApplicationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Manuální uzavření záznamu — closed_reason=MANUAL.
        # closed_for_applications_at + closed_reason zapisuje service.
        try:
            practice = PracticeService.close_practice_for_applications(
                practice=practice,
                reason=ApplicationClosureReason.MANUAL,
                actor=request.user,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PracticeSerializer(practice).data)


class IsStudentOrStaff(permissions.BasePermission):
    """
    Allows students, STAG teachers, garant praxe, and admins.

    organizace (OrganizationUser s employer_profile) smí vytvářet
    externí praxe pouze se schváleným profilem — jinak 403 EMPLOYER_NOT_APPROVED.
    """

    def has_permission(self, request, view):
        from users.models import StudentUser
        from users.permissions import IsApprovedOrganization, IsGarantPraxe, IsStagTeacher

        user = request.user
        if not user or not user.is_authenticated:
            return False
        if isinstance(user, StudentUser):
            return True
        if user.is_superuser:
            return True
        if IsStagTeacher().has_permission(request, view) or IsGarantPraxe().has_permission(request, view):
            return True
        # Organizace (např. pro pobočku/partnera bez registrace) — jen APPROVED.
        if getattr(user, "employer_profile", None):
            return IsApprovedOrganization().has_permission(request, view)
        return False


class ExternalPracticeView(APIView):
    """
    POST /api/practices/external/
    Vytvoří mimosystémovou praxi (bez registrované firmy).
    """

    permission_classes = [IsAuthenticated, IsStudentOrStaff]

    @extend_schema(
        summary="Create external practice",
        description="Vytvoří mimosystémovou praxi — pro studenty nebo školy, kde firma není registrována v systému.",
        tags=["Practices - External"],
        request=ExternalPracticeSerializer,
        responses={201: PracticeSerializer},
    )
    def post(self, request):
        serializer = ExternalPracticeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # BE-013: atomický create+apply — buď vznikne právě jeden Practice
        # + jedna StudentPractice, nebo se vše rollbackne a vrací se čistá
        # chyba. Nikdy 201-warning bez StudentPractice ani osiřelý Practice.
        try:
            with transaction.atomic():
                practice = serializer.save()

                ActionLogService.log(
                    user=request.user,
                    action_type=ActionLogType.CREATE,
                    object_type="Practice",
                    object_id=practice.pk,
                    description=f"Vytvoření mimosystémové praxe '{practice.title}' uživatelem {request.user.email}",
                )

                # If a student creates, automatically apply them
                if isinstance(request.user, StudentUser):
                    from practices.services import PracticeService

                    PracticeService.apply_student_practice(request.user, practice.pk)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PracticeSerializer(practice).data, status=status.HTTP_201_CREATED)
