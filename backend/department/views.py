from django.db.models import Prefetch
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.decorators import role_required
from api.views import StandardResultsSetPagination
from department.models import Department
from student_practices.models import StudentPractice
from users.models import (
    OrganizationRole,
    ProfessorUser,
    StagRoleEnum,
    StudentUser,
    UserSubject,
    UserSubjectType,
)
from users.services import get_user_department_ids

from .serializers import (
    AdminDepartmentSerializer,
    DepartmentUserSerializer,
    ProfessorDetailSerializer,
    StudentDetailSerializer,
)


class DepartmentStudentListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        dept_ids = get_user_department_ids(user)

        if not dept_ids:
            return StudentUser.objects.none()

        # Optimized query using joins instead of lists
        return (
            StudentUser.objects.filter(
                user_subjects__subject__department_id__in=dept_ids,
                user_subjects__role=UserSubjectType.Student.value,
            )
            .distinct()
            .select_related("stag_role")
            .prefetch_related(
                Prefetch(
                    "student_practices",
                    queryset=StudentPractice.objects.select_related("practice"),
                )
            )
        )


class DepartmentUserRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentUserSerializer
    permission_classes = [IsAuthenticated]


class DepartmentProfessorListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        dept_ids = get_user_department_ids(self.request.user)

        if not dept_ids:
            return ProfessorUser.objects.none()

        professors = ProfessorUser.objects.filter(department_id__in=dept_ids, department_role=UserSubjectType.Professor.value).distinct()

        print(f"Found {professors.count()} professor(s)")

        return professors.prefetch_related(
            Prefetch(
                "user_subjects",
                queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject"),
            )
        )


class AllDepartmentProfessorListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        # All professors across all departments
        qs = ProfessorUser.objects.all().distinct()
        return qs.prefetch_related(
            Prefetch(
                "user_subjects",
                queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject"),
            )
        )


class AdminDepartmentViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminDepartmentSerializer

    queryset = Department.objects.all()
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/admin-department/{id}/
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/admin-department/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practices/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
