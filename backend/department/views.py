from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.views import StandardResultsSetPagination
from department.models import Department
from department.services import (
    get_all_professors,
    get_department_professors,
    get_department_students,
)
from users.action_log import ActionLogService
from users.constants import ActionLogType
from users.models import ProfessorUser
from users.permissions import IsOrganizationUser, IsStagTeacher
from users.serializers import ProfessorUserProfileSerializer

from .serializers import (
    AdminDepartmentSerializer,
    DepartmentUserSerializer,
    ProfessorDetailSerializer,
    StudentDetailSerializer,
)


class DepartmentProfessorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProfessorUser.objects.all()
    serializer_class = ProfessorUserProfileSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        instance = serializer.save()

        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.UPDATE,
            object_type="ProfessorUser",
            object_id=instance.pk,
            description=f"Úprava profesora {instance.email} (ID: {instance.pk})",
        )

    def perform_destroy(self, instance):
        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.DELETE,
            object_type="ProfessorUser",
            object_id=instance.pk,
            description=f"Smazání profesora {instance.email} (ID: {instance.pk})",
        )
        instance.delete()


class DepartmentStudentListView(generics.ListAPIView):
    @extend_schema(
        summary="List students in department",
        description=(
            "Returns a list of students belonging to the same department as the logged-in user. **Permissions: Authenticated User**"
        ),
        tags=["Department"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        return get_department_students(self.request.user)


class DepartmentUserRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    @extend_schema(
        summary="Retrieve/Update/Delete department user role",
        description="Manages a specific user's role within a department. **Permissions: Authenticated User**",
        tags=["Department"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update department user role",
        description="Updates the role of a user within a department. **Permissions: Authenticated User**",
        tags=["Department"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update department user role",
        description="Partially updates the role of a user within a department. **Permissions: Authenticated User**",
        tags=["Department"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete department user role",
        description="Removes a user's role from a department. **Permissions: Authenticated User**",
        tags=["Department"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    queryset = Department.objects.all()
    serializer_class = DepartmentUserSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        instance = serializer.save()

        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.UPDATE,
            object_type="Department",
            object_id=instance.department_id,
            description=f"Úprava role na katedře {instance.department_name} (ID: {instance.department_id})",
        )

    def perform_destroy(self, instance):
        ActionLogService.log(
            user=self.request.user,
            action_type=ActionLogType.DELETE,
            object_type="Department",
            object_id=instance.department_id,
            description=f"Smazání role na katedře {instance.department_name} (ID: {instance.department_id})",
        )
        instance.delete()


class DepartmentProfessorListView(generics.ListAPIView):
    @extend_schema(
        summary="List professors in department",
        description=(
            "Returns a list of professors belonging to the same department as the logged-in user. **Permissions: Authenticated User**"
        ),
        tags=["Department"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        return get_department_professors(self.request.user)


class AllDepartmentProfessorListView(generics.ListAPIView):
    @extend_schema(
        summary="List all professors across all departments",
        description="Returns a comprehensive list of all professors in the system. **Permissions: Authenticated User**",
        tags=["Department"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        return get_all_professors()


class AdminDepartmentViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminDepartmentSerializer

    queryset = Department.objects.all()
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), (IsOrganizationUser | IsStagTeacher)()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/admin-department/
        departments = self.queryset
        page = self.paginate_queryset(departments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/admin-department/{id}/
        department = self.get_object()
        serializer = self.get_serializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.CREATE,
            object_type="Department",
            object_id=serializer.data.get("department_id"),
            description=f"Vytvoření katedry: {serializer.data.get('department_name', '')}",
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.UPDATE,
            object_type="Department",
            object_id=pk,
            description=f"Úprava katedry {instance.department_name} (ID: {pk})",
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/admin-department/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()

        ActionLogService.log(
            user=request.user,
            action_type=ActionLogType.DELETE,
            object_type="Department",
            object_id=pk,
            description=f"Smazání katedry {instance.department_name} (ID: {pk})",
        )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
