from api.models import Department, StagUser, StudentPractice, UserSubjectType
from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .serializers import DepartmentSerializer, StudentDetailSerializer


class DepartmentStudentListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        # departments where current user has any role
        dept_ids = Department.objects.filter(user=self.request.user).values_list("department_id", flat=True)

        # students enrolled in subjects of those departments
        return (
            StagUser.objects.filter(usersubject__subject__department_id__in=dept_ids, usersubject__role=UserSubjectType.Student)
            .distinct()
            .select_related("stag_role")
            .prefetch_related(
                Prefetch(
                    "studentpractice_set", queryset=StudentPractice.objects.select_related("practice", "approval_status", "progress_status")
                )
            )
        )


class DepartmentUserRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
