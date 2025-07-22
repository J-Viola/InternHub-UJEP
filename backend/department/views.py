from api.models import Department, ProfessorUser, StudentPractice, StudentUser, UserSubject, UserSubjectType, Subject
from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .serializers import DepartmentSerializer, ProfessorDetailSerializer, StudentDetailSerializer, DepartmentUserSerializer


class DepartmentStudentListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StudentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # Zjisti department_id podle přihlášeného profesora
        department_id = None
        if hasattr(user, 'professoruser') and user.professoruser.department_id:
            department_id = user.professoruser.department_id
        else:
            # fallback: pokud není přímo ProfessorUser, zkusit přes UserSubject
            department_id = (
                Department.objects.filter(subjects__user_subjects__user=user).values_list("department_id", flat=True).first()
            )
        if not department_id:
            return StudentUser.objects.none()
        # Najdi všechny subjects pod tímto departmentem
        subject_ids = (
            Subject.objects.filter(department_id=department_id).values_list("subject_id", flat=True)
        )
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
    serializer_class = DepartmentSerializer
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
