from django.db.models import Prefetch

from student_practices.models import StudentPractice
from users.models import ProfessorUser, StudentUser, UserSubject, UserSubjectType
from users.services import get_user_department_ids


def get_department_students(user):
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


def get_department_professors(user):
    dept_ids = get_user_department_ids(user)

    if not dept_ids:
        return ProfessorUser.objects.none()

    professors = ProfessorUser.objects.filter(department_id__in=dept_ids, department_role=UserSubjectType.Professor.value).distinct()

    return professors.prefetch_related(
        Prefetch(
            "user_subjects",
            queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject"),
        )
    )


def get_all_professors():
    # All professors across all departments
    qs = ProfessorUser.objects.all().distinct()
    return qs.prefetch_related(
        Prefetch(
            "user_subjects",
            queryset=UserSubject.objects.filter(role=UserSubjectType.Professor.value).select_related("subject"),
        )
    )
