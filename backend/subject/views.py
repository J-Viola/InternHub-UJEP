from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from practices.messages import PracticeMessages
from subject.models import Subject
from subject.permissions import IsTeacherOrAdmin
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.services import get_user_department_ids

from .serializers import SubjectSerializer


@extend_schema(tags=["Subjects"])
class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subjects.
    """

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["department", "subject_code"]
    search_fields = ["subject_name", "subject_code"]
    ordering_fields = ["subject_name", "subject_code", "department__department_name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsTeacherOrAdmin()]
        return [permissions.IsAuthenticated()]

    @extend_schema(summary="List all subjects")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Create a new subject")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Get subject detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Update a subject")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Partial update a subject")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Delete a subject")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()

        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.CREATE,
            object_type="Subject",
            object_id=instance.pk,
            description=f"Vytvoření předmětu {instance.subject_name} ({instance.subject_code})",
        )

    def perform_update(self, serializer):
        instance = serializer.save()

        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.UPDATE,
            object_type="Subject",
            object_id=instance.pk,
            description=f"Úprava předmětu {instance.subject_name} ({instance.subject_code})",
        )

    def perform_destroy(self, instance):
        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.DELETE,
            object_type="Subject",
            object_id=instance.pk,
            description=f"Smazání předmětu {instance.subject_name} ({instance.subject_code})",
        )
        instance.delete()

    @extend_schema(
        summary="Get department-specific subjects",
        description=(
            "Returns all subjects belonging to the department(s) associated with the logged-in professor. "
            "**Permissions: Authenticated Professor**"
        ),
        responses={
            200: SubjectSerializer(many=True),
            400: OpenApiResponse(description="User has no assigned department"),
        },
    )
    @action(detail=False, methods=["get"], url_path="department-subjects")
    def department_subjects(self, request):
        """
        Get all subjects from the department where the logged-in user is a professor.
        Only accessible by users with assigned department.
        """
        dept_ids = get_user_department_ids(request.user)

        if not dept_ids:
            return Response({"error": PracticeMessages.NO_DEPARTMENT}, status=400)

        # Get all subjects from the user's departments
        subjects = Subject.objects.filter(department_id__in=dept_ids).select_related("department")

        # Serialize the subjects
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)
