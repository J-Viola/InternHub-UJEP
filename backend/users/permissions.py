from rest_framework import permissions

from users.models import (
    OrganizationUser,
    ProfessorUser,
    UserSubjectType,
)


class CanViewStudentProfile(permissions.BasePermission):
    """
    Custom permission to allow access to student profile only for:
    - The student themselves
    - Admins
    - Organizations where the student applied or was invited
    - Professors from the same department (via subjects)
    """

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
        if isinstance(user, ProfessorUser) and user.department:
            # Check if student has any subject from this department (as a Student)
            # We check UserSubject where user is the student (obj) and subject belongs to professor's department
            has_subject = obj.user_subjects.filter(subject__department=user.department, role=UserSubjectType.Student).exists()

            if has_subject:
                return True

        return False
