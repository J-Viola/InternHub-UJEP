from django.db.models import Q

from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    User,
    UserSubjectType,
)


def student_practice_scope_q(user) -> Q:
    """
    Vrátí ``Q`` filtr přihlášek (StudentPractice), k danému uživateli smí
    přistupovat. Používá ho object-level guard (potvrzení smlouvy, evaluace)
    i queryset scoping, aby obě vrstvy měly totožnou definici rozsahu.

    Fail-closed kontrakt:
    - superuser → ``Q()`` (celý rozsah),
    - neautentizovaný / neznámá role → ``Q(pk__in=[])`` (žádné řádky),
    - student → pouze vlastní přihlášky,
    - organizace → pouze přihlášky praxe svého employer profilu,
    - profesor → přihlášky praxí předmětů, které vyučuje / řídí, případně
      celé své katedry (HEAD / garant praxe); praxe bez předmětu ani cizí
      katedra neprocházejí.
    """
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    if user.is_superuser:
        return Q()

    scope = Q(pk__in=[])

    if isinstance(user, StudentUser):
        scope |= Q(user_id=user.pk)
    elif isinstance(user, OrganizationUser):
        employer = getattr(user, "employer_profile", None)
        if employer is not None:
            scope |= Q(practice__employer_id=employer.pk)
    elif isinstance(user, ProfessorUser):
        from subject.models import Subject

        subject_ids = set(user.user_subjects.filter(role=UserSubjectType.Professor).values_list("subject_id", flat=True))
        subject_ids.update(Subject.objects.filter(subject_manager_id=user.pk).values_list("subject_id", flat=True))
        if user.department_id and (user.department_role == DepartmentRole.HEAD or user.is_garant_praxe):
            subject_ids.update(Subject.objects.filter(department_id=user.department_id).values_list("subject_id", flat=True))
        if subject_ids:
            scope |= Q(practice__subject_id__in=list(subject_ids))

    return scope


def user_can_access_student_practice(user, student_practice) -> bool:
    """
    Object-level existence check nad ``student_practice_scope_q`` —
    fail-closed: žádný vztah = přístup zamítnut.
    """
    if student_practice is None:
        return False
    from student_practices.models import StudentPractice

    return StudentPractice.objects.filter(student_practice_scope_q(user)).filter(pk=student_practice.pk).exists()


def can_approve_practice(user: User, student_practice) -> bool:
    """
    Centralized logic to check if a user can approve a given student practice.
    Used in serializers and permissions.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Use isinstance checks (consistent with can_manage_practice)
    is_professor = isinstance(user, ProfessorUser)
    is_org = isinstance(user, OrganizationUser)

    if is_professor:
        practice_subject = student_practice.practice.subject
        if not practice_subject:
            return False

        # 1. Vedoucí katedry
        if user.department_role == DepartmentRole.HEAD:
            if user.department_id == practice_subject.department_id:
                return True

        # 1a. Garant Praxe — oprávnění napříč katedrou
        if user.is_garant_praxe:
            if user.department_id == practice_subject.department_id:
                return True

        # 2. Garant předmětu
        if practice_subject.subject_manager_id == user.user_id:
            return True

        # 3. Vyučující předmětu
        if hasattr(user, "user_subjects"):
            if user.user_subjects.filter(subject=practice_subject, role=UserSubjectType.Professor).exists():
                return True

    if is_org:
        # If already approved by employer, can't approve again
        if student_practice.employer_approved:
            return False

        if hasattr(user, "employer_profile") and student_practice.practice.employer_id == user.employer_profile_id:
            return True

    return False
