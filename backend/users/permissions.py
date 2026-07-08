from rest_framework import permissions

from users.models import (
    DepartmentRole,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRoleEnum,
    StagUser,
    StudentUser,
    UserSubjectType,
)


def _is_stag_admin_or_head(user) -> bool:
    """
    True if user is a superuser, has STAG role VK, or is a department HEAD.

    Used by IsStagAdmin and CanCancel* permission classes.
    Ref: N12 — IsStagAdmin nepokrýval DepartmentRole.HEAD.
    """
    if user.is_superuser:
        return True
    if isinstance(user, ProfessorUser):
        if user.stag_role and user.stag_role.role.lower() == StagRoleEnum.VK:
            return True
        if user.department_role == DepartmentRole.HEAD:
            return True
    return False


class IsOrganizationUser(permissions.BasePermission):
    """
    Allows access only to organization users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and isinstance(request.user, OrganizationUser))

    def has_object_permission(self, request, view, obj):
        # obj can be Practice or other models related to EmployerProfile
        if hasattr(obj, "employer"):
            return obj.employer == request.user.employer_profile
        if hasattr(obj, "employer_profile"):
            return obj.employer_profile == request.user.employer_profile
        return False


class IsOrganizationOwner(permissions.BasePermission):
    """
    Allows access only to organization owners.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, OrganizationUser)
            and request.user.organization_role == OrganizationRole.OWNER
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "employer"):
            return obj.employer == request.user.employer_profile
        if hasattr(obj, "employer_profile"):
            return obj.employer_profile == request.user.employer_profile
        return False


class IsStagUser(permissions.BasePermission):
    """
    Allows access only to STAG users (students or professors).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and isinstance(request.user, StagUser))


class IsStagStudent(permissions.BasePermission):
    """
    Allows access only to students (STAG role 'st').
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and isinstance(request.user, StudentUser))


class IsStagTeacher(permissions.BasePermission):
    """
    Allows access only to teachers with active STAG role 'vy' (Vyučující).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and isinstance(user, ProfessorUser)
            and user.stag_role is not None
            and user.stag_role.role.lower() == StagRoleEnum.VY
        )

    def has_object_permission(self, request, view, obj):
        """
        Object-level: verify the professor belongs to the subject's department.

        Ref: CR-DEPT-2 — when obj is a ProfessorUser (e.g. department professor
        operations), check that the requesting teacher and the target professor
        belong to the same department.
        Ref: H-PRAC-1 — practices without a subject (orphans) are no longer
        accessible to non-admin teachers, closing a department-scope bypass.
        """
        user = request.user
        if not user or not isinstance(user, ProfessorUser):
            return False

        # CR-DEPT-2: If obj is a ProfessorUser (e.g., department professor
        # CRUD operations), verify same department to prevent a teacher from
        # editing/deleting professors from other departments.
        if isinstance(obj, ProfessorUser):
            user_dept_id = getattr(user, "department_id", None)
            obj_dept_id = getattr(obj, "department_id", None)
            return user_dept_id is not None and user_dept_id == obj_dept_id

        # Get the practice from the object (could be Practice or StudentPractice)
        practice = getattr(obj, "practice", obj)
        if not hasattr(practice, "subject"):
            return False  # H-PRAC-1: No subject link → cannot verify department → deny
        subject = practice.subject
        if subject is None:
            return False  # H-PRAC-1: Null subject → cannot verify department → deny
        # Check department match
        user_dept = getattr(user, "department", None)
        user_dept_id = getattr(user, "department_id", None)
        if user_dept_id is not None and subject.department_id == user_dept_id:
            return True
        if user_dept is not None and subject.department_id == user_dept.pk:
            return True
        return False


class IsStagAdmin(permissions.BasePermission):
    """
    Allows access only to STAG admins (STAG role 'vk') or department heads.

    Ref: N12 — rozšířeno o DepartmentRole.HEAD (WP3.3).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _is_stag_admin_or_head(request.user))


class HasRolePermission(permissions.BasePermission):
    """
    Checks if the view's ``required_roles`` attribute contains the user's role.
    Returns True when the view defines no required_roles.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        required_roles = getattr(view, "required_roles", [])
        if not required_roles:
            return True

        if isinstance(request.user, OrganizationUser):
            return request.user.organization_role in required_roles

        if hasattr(request.user, "stag_role") and request.user.stag_role:
            return request.user.stag_role.role in required_roles

        return request.user.is_superuser


class CanViewStudentProfile(permissions.BasePermission):
    """
    Custom permission to allow access to student profile only for:
    - The student themselves
    - Admins
    - Organizations where the student applied or was invited
    - Professors from the same department (via subjects)
    """

    def has_permission(self, request, view):
        # Allow any authenticated user to try to access a student profile.
        # The specific object-level logic in has_object_permission will filter them.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # obj is StudentUser instance
        user = request.user

        # 1. Own profile
        if user == obj:
            return True

        # 2. Admin
        if user.is_superuser:
            return True

        # 3. Organization
        if isinstance(user, OrganizationUser) and user.employer_profile:
            # Check if student applied to any practice of this employer
            has_application = obj.student_practices.filter(practice__employer=user.employer_profile).exists()
            # Check if student was invited by this employer
            has_invitation = obj.employer_invitations.filter(employer=user.employer_profile).exists()

            if has_application or has_invitation:
                return True

        # 4. Professor
        if isinstance(user, ProfessorUser):
            from django.db.models import Q

            dept_ids = [user.department_id] if user.department_id else []
            if not dept_ids:
                dept_ids = list(
                    user.user_subjects.filter(role=UserSubjectType.Professor).values_list("subject__department_id", flat=True).distinct()
                )

            # Check if student is in any department the professor belongs to
            # OR if professor manages a subject the student is in
            has_subject = obj.user_subjects.filter(
                Q(subject__department_id__in=dept_ids) | Q(subject__subject_manager=user),
                role=UserSubjectType.Student,
            ).exists()

            if has_subject:
                return True

        return False


# ========================================================================
# WP3 — Nové permission třídy pro state machine
# ========================================================================


class IsNotCancelled(permissions.BasePermission):
    """
    Guard: blocks mutations on cancelled Practice / StudentPractice entities.

    Používá se jako base check pro všechny mutation views.
    Vrací HTTP 403, pokud je objekt stornován (is_cancelled=True).

    Ref: WP3.1, THESIS_ARCHITECTURE_PLAN.md 5.2
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(obj, "is_cancelled", False):
            return False
        return True


class CanCancelPractice(permissions.BasePermission):
    """
    Kdo může stornovat nabídku praxe (Practice):
    - Admin / superuser
    - Vedoucí katedry (DepartmentRole.HEAD) daného subjectu
    - Garant Praxe (is_garant_praxe flag)

    Ref: WP3.2, OQ4, THESIS_ARCHITECTURE_PLAN.md sekce 3.4
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Department HEAD check: same department as practice's subject
        if isinstance(user, ProfessorUser) and user.department_role == DepartmentRole.HEAD:
            subject = getattr(obj, "subject", None)
            if subject and user.department == subject.department:
                return True

        # Garant Praxe — must match practice's department (H-PRAC-3)
        if isinstance(user, ProfessorUser) and user.is_garant_praxe:
            subject = getattr(obj, "subject", None)
            if subject and hasattr(user, "department_id") and subject.department_id == user.department_id:
                return True
            if subject and hasattr(user, "department") and subject.department_id == user.department.pk:
                return True

        return False


class CanCancelStudentPractice(permissions.BasePermission):
    """
    Kdo může stornovat přihlášku studenta (StudentPractice):
    - Admin / superuser
    - Vedoucí katedry (DepartmentRole.HEAD) daného subjectu
    - Garant Praxe (is_garant_praxe flag)
    - Zaměstnavatel (OrganizationUser) — vlastník praxe
    - Student (vlastník přihlášky) — POUZE do stavu PRELIMINARY_APPROVED (včetně)

    Ref: WP3.2, WP3.5 (N10), OQ4
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Department HEAD check
        if isinstance(user, ProfessorUser) and user.department_role == DepartmentRole.HEAD:
            practice = getattr(obj, "practice", None)
            if practice:
                subject = getattr(practice, "subject", None)
                if subject and user.department == subject.department:
                    return True

        # Garant Praxe — must match practice's department
        if isinstance(user, ProfessorUser) and user.is_garant_praxe:
            practice = getattr(obj, "practice", None)
            if practice:
                subject = getattr(practice, "subject", None)
                if subject and hasattr(user, "department_id") and subject.department_id == user.department_id:
                    return True
                if subject and hasattr(user, "department") and subject.department_id == user.department.pk:
                    return True

        # Employer who owns the practice
        if isinstance(user, OrganizationUser):
            practice = getattr(obj, "practice", None)
            if practice and hasattr(user, "employer_profile"):
                if practice.employer == user.employer_profile:
                    return True

        # Student who owns the SP — only up to PRELIMINARY_APPROVED (N10)
        if isinstance(user, StudentUser) and obj.user == user:
            from student_practices.models import StudentPracticeWorkflowState

            allowed_states = (
                StudentPracticeWorkflowState.APPLIED,
                StudentPracticeWorkflowState.PRELIMINARY_APPROVED,
            )
            if obj.workflow_state in allowed_states:
                return True

        return False


class IsStudentPracticeAccessible(permissions.BasePermission):
    """
    Access to StudentPractice documents — student owner, supervising professor,
    dept head, org owner, garant, or admin.

    Called against a StudentPractice object (obj.user = student, obj.practice = practice).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if _is_stag_admin_or_head(user):
            return True

        from users.models import OrganizationUser, ProfessorUser, StudentUser, UserSubjectType

        # Garant Praxe — must match practice's department (CR-2 fix)
        if isinstance(user, ProfessorUser) and user.is_garant_praxe:
            practice = getattr(obj, "practice", obj)
            if practice:
                subject = getattr(practice, "subject", None)
                if subject and hasattr(user, "department_id") and subject.department_id == user.department_id:
                    return True
        if isinstance(user, StudentUser) and obj.user_id == user.pk:
            return True
        if isinstance(user, OrganizationUser) and user.employer_profile and obj.practice.employer_id == user.employer_profile.pk:
            return True
        if isinstance(user, ProfessorUser):
            subject_ids = user.user_subjects.filter(role=UserSubjectType.Professor).values_list("subject_id", flat=True)
            if obj.practice.subject_id in subject_ids:
                return True
        return False


class IsGarantPraxe(permissions.BasePermission):
    """
    Povolí přístup pouze uživatelům s příznakem Garant Praxe.

    Varianta C dle THESIS_ARCHITECTURE_PLAN.md sekce 2.2.6.

    Ref: CR-PRAC-1 — added has_object_permission to prevent horizontal
    privilege escalation (garant could mutate any practice in the system).
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and isinstance(request.user, ProfessorUser) and request.user.is_garant_praxe
        )

    def has_object_permission(self, request, view, obj):
        """
        Object-level: garant praxe can only operate on practices within
        their own department. Prevents bypassing department-scoped authorization.

        obj can be a Practice or a StudentPractice (which has .practice -> Practice).
        The department is determined from practice.subject.department.
        """
        user = request.user
        if not isinstance(user, ProfessorUser) or not user.is_garant_praxe:
            return False

        # obj can be Practice or StudentPractice (which has .practice -> Practice)
        practice = getattr(obj, "practice", obj)

        # Get the subject from the practice
        if not hasattr(practice, "subject"):
            return False
        subject = practice.subject
        if subject is None:
            return False

        # Check department match — garant can only work on their own department's practices
        user_dept_id = getattr(user, "department_id", None)
        if user_dept_id is not None and subject.department_id == user_dept_id:
            return True

        user_dept = getattr(user, "department", None)
        if user_dept is not None and subject.department_id == user_dept.pk:
            return True

        return False


class IsAdminUser(permissions.BasePermission):
    """
    Custom IsAdminUser that explicitly checks has_object_permission.

    DRF's built-in permissions.IsAdminUser inherits has_object_permission = True
    from BasePermission, which causes OR-combined permission expressions
    (e.g. IsStagTeacher | permissions.IsAdminUser) to evaluate to True for
    ANY authenticated user at the object level, bypassing all other checks.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
