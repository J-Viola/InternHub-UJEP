from api.models import Department, StudentPractice, StudentUser, UserSubject, UserSubjectType
from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .serializers import DepartmentSerializer, StudentDetailSerializer, ProfessorDetailSerializer


class DepartmentStudentListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        # departments where current user has any role
        dept_ids = (
            Department.objects.filter(subjects__user_subjects__user=self.request.user).values_list("department_id", flat=True).distinct()
        )

        student_ids = (
            UserSubject.objects.filter(subject__department_id__in=dept_ids, role=UserSubjectType.Student.value)
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
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]


class DepartmentProfessorListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfessorDetailSerializer

    def get_queryset(self):
        # departments where current user has any role
        dept_ids = (
            Department.objects.filter(subjects__user_subjects__user=self.request.user)
            .values_list("department_id", flat=True)
            .distinct()
        )

        professor_ids = (
            UserSubject.objects.filter(
                subject__department_id__in=dept_ids,
                role=UserSubjectType.Professor.value
            )
            .values_list("user__user_ptr_id", flat=True)
            .distinct()
        )

        professors = StudentUser.objects.filter(user_id__in=professor_ids).distinct()

        print(f"Found {professors.count()} professor(s)")

        return professors.prefetch_related(
            Prefetch(
                "user_subjects",
                queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject")
            )
        )
