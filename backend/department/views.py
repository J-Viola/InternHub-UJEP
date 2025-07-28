from api.decorators import role_required
from api.models import Department, OrganizationRole, ProfessorUser, StudentPractice, StudentUser, Subject, UserSubject, UserSubjectType
from api.views import StandardResultsSetPagination
from django.db.models import Prefetch
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from users.models import StagRoleEnum

from .serializers import AdminDepartmentSerializer, DepartmentUserSerializer, ProfessorDetailSerializer, StudentDetailSerializer


class DepartmentStudentListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # Zjisti department_id podle přihlášeného profesora
        department_id = None
        if isinstance(user, ProfessorUser) and user.department_id:
            department_id = user.department_id
        else:
            # fallback: pokud není přímo ProfessorUser, zkusit přes UserSubject
            department_id = Department.objects.filter(subjects__user_subjects__user=user).values_list("department_id", flat=True).first()

        if not department_id:
            return StudentUser.objects.none()
        # Najdi všechny subjects pod tímto departmentem
        subject_ids = Subject.objects.filter(department_id=department_id).values_list("subject_id", flat=True)
        # Najdi všechny studenty, kteří mají alespoň jeden z těchto subjects
        student_ids = (
            UserSubject.objects.filter(subject_id__in=subject_ids, role=UserSubjectType.Student.value)
            .values_list("user__user_ptr_id", flat=True)
            .distinct()
        )
        students = StudentUser.objects.filter(user_id__in=student_ids).distinct()
        print(f"Found {students.count()} student(s)")
        return students.select_related("stag_role").prefetch_related(
            Prefetch("student_practices", queryset=StudentPractice.objects.select_related("practice"))
        )


class DepartmentUserRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentUserSerializer
    permission_classes = [IsAuthenticated]


class DepartmentProfessorListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        # departments where current user has any role
        dept_ids = (
            Department.objects.filter(subjects__user_subjects__user=self.request.user).values_list("department_id", flat=True).distinct()
        )

        professors = ProfessorUser.objects.filter(department_id__in=dept_ids, department_role=UserSubjectType.Professor.value).distinct()

        print(f"Found {professors.count()} professor(s)")

        return professors.prefetch_related(
            Prefetch("user_subjects", queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject"))
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
