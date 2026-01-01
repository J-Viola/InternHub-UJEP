from users.models import DepartmentRole, ProfessorUser, User, UserSubjectType


def can_approve_practice(user: User, student_practice) -> bool:
    """
    Centralized logic to check if a user can approve a given student practice.
    Used in serializers and permissions.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Robust role identification
    user_role = getattr(user, "role", "N/A")
    is_professor = user_role in ["VY", "VK"]
    is_org = user_role in ["OWNER", "INSERTER"]

    if is_professor:
        # If already approved by school, can't approve again
        if student_practice.school_approved:
            return False

        practice_subject = student_practice.practice.subject
        if not practice_subject:
            return False

        # 1. Vedoucí katedry
        prof_profile = getattr(user, "professor_user", user)
        if isinstance(prof_profile, ProfessorUser):
            if prof_profile.department_role == DepartmentRole.HEAD:
                if prof_profile.department_id == practice_subject.department_id:
                    return True

        # 2. Garant předmětu
        if practice_subject.subject_manager_id == user.user_id:
            return True

        # 3. Vyučující předmětu
        if hasattr(user, "user_subjects"):
            if user.user_subjects.filter(
                subject=practice_subject, role=UserSubjectType.Professor
            ).exists():
                return True

    if is_org:
        # If already approved by employer, can't approve again
        if student_practice.employer_approved:
            return False

        if (
            hasattr(user, "employer_profile")
            and student_practice.practice.employer_id == user.employer_profile_id
        ):
            return True

    return False
