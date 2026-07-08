from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    User,
    UserSubjectType,
)


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

        # 1a. Garant Praxe — oprávnění napříč katedrou (WP3.4)
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
