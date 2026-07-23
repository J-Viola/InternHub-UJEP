from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from department.models import Department
from student_practices.models import EmployerInvitation, EmployerInvitationStatus
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagRoleEnum,
    StudentUser,
    UserSubject,
    UserSubjectType,
)
from users.permissions import (
    CanViewStudentProfile,
    HasRolePermission,
    IsGarantOrReadOnly,
    IsOrganizationOrReadOnly,
    IsOrganizationOwner,
    IsOrganizationUser,
    IsStagAdmin,
    IsStagStudent,
    IsStagTeacher,
    IsStagUser,
    IsStudentOwner,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_request(user):
    req = RequestFactory().get("/")
    req.user = user
    return req


def make_org_user(email, role=OrganizationRole.OWNER, profile=None):
    user = OrganizationUser.objects.create(
        email=email,
        first_name="Org",
        last_name="User",
        is_active=True,
        organization_role=role,
    )
    if profile:
        user.employer_profile = profile
        user.save()
    return user


def make_student(email="student@test.com"):
    return StudentUser.objects.create(
        email=email,
        first_name="Jan",
        last_name="Student",
        is_active=True,
    )


def make_professor(email, department, role_str="vy"):
    stag_role, _ = StagRole.objects.get_or_create(role=role_str)
    return ProfessorUser.objects.create(
        email=email,
        first_name="Karel",
        last_name="Prof",
        is_active=True,
        department=department,
        stag_role=stag_role,
    )


def make_employer_profile():
    return EmployerProfile.objects.create(
        company_name="Test Corp",
        approval_status=ApprovalStatus.APPROVED,
    )


# ===========================================================================
# IsOrganizationUser
# ===========================================================================


class IsOrganizationUserTests(TestCase):
    def setUp(self):
        self.perm = IsOrganizationUser()
        self.org = make_org_user("org@test.com")
        self.student = make_student()

    def test_grants_authenticated_org_user(self):
        self.assertTrue(self.perm.has_permission(make_request(self.org), None))

    def test_denies_student(self):
        self.assertFalse(self.perm.has_permission(make_request(self.student), None))

    def test_denies_anonymous(self):
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), None))


# ===========================================================================
# IsOrganizationOwner
# ===========================================================================


class IsOrganizationOwnerTests(TestCase):
    def setUp(self):
        self.perm = IsOrganizationOwner()

    def test_grants_owner(self):
        owner = make_org_user("owner@test.com", role=OrganizationRole.OWNER)
        self.assertTrue(self.perm.has_permission(make_request(owner), None))

    def test_denies_inserter(self):
        inserter = make_org_user("inserter@test.com", role=OrganizationRole.INSERTER)
        self.assertFalse(self.perm.has_permission(make_request(inserter), None))

    def test_denies_student(self):
        student = make_student("s2@test.com")
        self.assertFalse(self.perm.has_permission(make_request(student), None))

    def test_denies_anonymous(self):
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), None))


# ===========================================================================
# IsStagUser
# ===========================================================================


class IsStagUserTests(TestCase):
    def setUp(self):
        self.perm = IsStagUser()
        self.dept = Department.objects.create(department_name="KI", department_code="KI")

    def test_grants_student(self):
        self.assertTrue(self.perm.has_permission(make_request(make_student()), None))

    def test_grants_professor(self):
        prof = make_professor("prof@test.com", self.dept)
        self.assertTrue(self.perm.has_permission(make_request(prof), None))

    def test_denies_org_user(self):
        org = make_org_user("org2@test.com")
        self.assertFalse(self.perm.has_permission(make_request(org), None))

    def test_denies_anonymous(self):
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), None))


# ===========================================================================
# IsStagStudent
# ===========================================================================


class IsStagStudentTests(TestCase):
    def setUp(self):
        self.perm = IsStagStudent()
        self.dept = Department.objects.create(department_name="KI2", department_code="KI2")

    def test_grants_student(self):
        self.assertTrue(self.perm.has_permission(make_request(make_student("s3@test.com")), None))

    def test_denies_professor(self):
        prof = make_professor("prof2@test.com", self.dept)
        self.assertFalse(self.perm.has_permission(make_request(prof), None))

    def test_denies_org_user(self):
        self.assertFalse(self.perm.has_permission(make_request(make_org_user("org3@test.com")), None))


# ===========================================================================
# IsStagTeacher
# ===========================================================================


class IsStagTeacherTests(TestCase):
    def setUp(self):
        self.perm = IsStagTeacher()
        self.dept = Department.objects.create(department_name="KI3", department_code="KI3")

    def test_grants_professor(self):
        prof = make_professor("prof3@test.com", self.dept)
        self.assertTrue(self.perm.has_permission(make_request(prof), None))

    def test_denies_student(self):
        self.assertFalse(self.perm.has_permission(make_request(make_student("s4@test.com")), None))

    def test_denies_org_user(self):
        self.assertFalse(self.perm.has_permission(make_request(make_org_user("org4@test.com")), None))


# ===========================================================================
# IsStagAdmin
# ===========================================================================


class IsStagAdminTests(TestCase):
    def setUp(self):
        self.perm = IsStagAdmin()
        self.dept = Department.objects.create(department_name="KI4", department_code="KI4")

    def test_grants_vk_professor(self):
        prof = make_professor("vk@test.com", self.dept, role_str=StagRoleEnum.VK)
        self.assertTrue(self.perm.has_permission(make_request(prof), None))

    def test_denies_vy_professor(self):
        prof = make_professor("vy@test.com", self.dept, role_str=StagRoleEnum.VY)
        self.assertFalse(self.perm.has_permission(make_request(prof), None))

    def test_denies_student(self):
        self.assertFalse(self.perm.has_permission(make_request(make_student("s5@test.com")), None))

    def test_denies_anonymous(self):
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), None))


# ===========================================================================
# HasRolePermission
# ===========================================================================


class _MockView:
    required_roles = []


class HasRolePermissionTests(TestCase):
    def setUp(self):
        self.perm = HasRolePermission()

    def test_passes_when_no_required_roles(self):
        view = _MockView()
        view.required_roles = []
        user = make_org_user("org5@test.com")
        self.assertTrue(self.perm.has_permission(make_request(user), view))

    def test_passes_matching_org_role(self):
        view = _MockView()
        view.required_roles = [OrganizationRole.OWNER]
        owner = make_org_user("owner2@test.com", role=OrganizationRole.OWNER)
        self.assertTrue(self.perm.has_permission(make_request(owner), view))

    def test_denies_non_matching_org_role(self):
        view = _MockView()
        view.required_roles = [OrganizationRole.OWNER]
        inserter = make_org_user("ins2@test.com", role=OrganizationRole.INSERTER)
        self.assertFalse(self.perm.has_permission(make_request(inserter), view))

    def test_passes_superuser_regardless_of_roles(self):
        view = _MockView()
        view.required_roles = [OrganizationRole.OWNER]
        superuser = OrganizationUser.objects.create(
            email="su@test.com",
            first_name="Su",
            last_name="User",
            is_active=True,
            is_superuser=True,
        )
        self.assertTrue(self.perm.has_permission(make_request(superuser), view))

    def test_denies_anonymous(self):
        view = _MockView()
        view.required_roles = []
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), view))


# ===========================================================================
# CanViewStudentProfile
# ===========================================================================


class CanViewStudentProfileTests(TestCase):
    def setUp(self):
        self.perm = CanViewStudentProfile()
        self.dept = Department.objects.create(department_name="KI5", department_code="KI5")
        self.other_dept = Department.objects.create(department_name="KM5", department_code="KM5")

        self.student = make_student("target@test.com")

        self.profile = make_employer_profile()
        self.org_owner = make_org_user("owner3@test.com", profile=self.profile)

        self.other_profile = make_employer_profile()
        self.other_profile.company_name = "Other Corp"
        self.other_profile.save()
        self.other_org = make_org_user("other@test.com", profile=self.other_profile)

        self.prof_same = make_professor("ps@test.com", self.dept)
        self.prof_diff = make_professor("pd@test.com", self.other_dept, role_str="vk")

        self.subject = Subject.objects.create(subject_code="KI001", department=self.dept)
        UserSubject.objects.create(
            user=self.student,
            subject=self.subject,
            role=UserSubjectType.Student,
        )

    def _check(self, request_user, target=None):
        req = make_request(request_user)
        return self.perm.has_object_permission(req, None, target or self.student)

    def test_allows_own_profile(self):
        self.assertTrue(self._check(self.student))

    def test_allows_superuser(self):
        admin = OrganizationUser.objects.create(
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
        )
        self.assertTrue(self._check(admin))

    def test_allows_org_with_student_invitation(self):
        EmployerInvitation.objects.create(
            employer=self.profile,
            user=self.student,
            status=EmployerInvitationStatus.PENDING,
        )
        self.assertTrue(self._check(self.org_owner))

    def test_denies_org_without_connection(self):
        self.assertFalse(self._check(self.other_org))

    def test_allows_professor_same_department(self):
        self.assertTrue(self._check(self.prof_same))

    def test_denies_professor_different_department(self):
        self.assertFalse(self._check(self.prof_diff))

    def test_denies_unrelated_student(self):
        other_student = make_student("other_student@test.com")
        self.assertFalse(self._check(other_student))


# ===========================================================================
# IsGarantOrReadOnly
# ===========================================================================


def make_safe_request(user):
    """Simulate a GET request (safe method)."""
    req = RequestFactory().get("/")
    req.user = user
    return req


def make_unsafe_request(user):
    """Simulate a POST request (unsafe method)."""
    req = RequestFactory().post("/")
    req.user = user
    return req


class IsGarantOrReadOnlyTests(TestCase):
    def setUp(self):
        self.perm = IsGarantOrReadOnly()
        self.dept = Department.objects.create(department_name="KI6", department_code="KI6")

    def test_grants_vy_read(self):
        """VY (Vyučující) can read."""
        prof = make_professor("vy_prof@test.com", self.dept, role_str=StagRoleEnum.VY)
        self.assertTrue(self.perm.has_permission(make_safe_request(prof), None))

    def test_grants_vk_read(self):
        """VK (Vedoucí katedry) can read."""
        prof = make_professor("vk_prof@test.com", self.dept, role_str=StagRoleEnum.VK)
        self.assertTrue(self.perm.has_permission(make_safe_request(prof), None))

    def test_grants_vy_write(self):
        """VY can write."""
        prof = make_professor("vy_prof2@test.com", self.dept, role_str=StagRoleEnum.VY)
        self.assertTrue(self.perm.has_permission(make_unsafe_request(prof), None))

    def test_grants_vk_write(self):
        """VK can write."""
        prof = make_professor("vk_prof2@test.com", self.dept, role_str=StagRoleEnum.VK)
        self.assertTrue(self.perm.has_permission(make_unsafe_request(prof), None))

    def test_denies_student_write(self):
        """Student cannot write."""
        student = make_student("std@test.com")
        self.assertFalse(self.perm.has_permission(make_unsafe_request(student), None))

    def test_allows_student_read(self):
        """Student can read (safe method)."""
        student = make_student("std2@test.com")
        self.assertTrue(self.perm.has_permission(make_safe_request(student), None))

    def test_denies_anonymous(self):
        """Anonymous user is denied."""
        self.assertFalse(self.perm.has_permission(make_unsafe_request(AnonymousUser()), None))

    def test_denies_org_user_write(self):
        """Organization user cannot write."""
        org = make_org_user("org_isgarant@test.com")
        self.assertFalse(self.perm.has_permission(make_unsafe_request(org), None))


# ===========================================================================
# IsOrganizationOrReadOnly
# ===========================================================================


class IsOrganizationOrReadOnlyTests(TestCase):
    def setUp(self):
        self.perm = IsOrganizationOrReadOnly()
        self.profile = make_employer_profile()

    def test_grants_org_user_write(self):
        """Organization user with employer_profile can write."""
        org = make_org_user("org_write@test.com", profile=self.profile)
        self.assertTrue(self.perm.has_permission(make_unsafe_request(org), None))

    def test_allows_student_read(self):
        """Student can read."""
        student = make_student("std3@test.com")
        self.assertTrue(self.perm.has_permission(make_safe_request(student), None))

    def test_denies_student_write(self):
        """Student cannot write."""
        student = make_student("std4@test.com")
        self.assertFalse(self.perm.has_permission(make_unsafe_request(student), None))

    def test_denies_anonymous_write(self):
        """Anonymous user cannot write."""
        self.assertFalse(self.perm.has_permission(make_unsafe_request(AnonymousUser()), None))

    def test_denies_anonymous_read(self):
        """Anonymous user cannot read (not authenticated)."""
        self.assertFalse(self.perm.has_permission(make_safe_request(AnonymousUser()), None))

    def test_denies_org_user_without_profile_write(self):
        """Organization user without employer_profile cannot write."""
        org = make_org_user("org_no_profile@test.com")
        self.assertFalse(self.perm.has_permission(make_unsafe_request(org), None))


# ===========================================================================
# IsStudentOwner
# ===========================================================================


class IsStudentOwnerTests(TestCase):
    def setUp(self):
        self.perm = IsStudentOwner()
        self.student = make_student("owner_test@test.com")

    def test_grants_owner(self):
        """Student who owns the object is granted access."""
        req = make_request(self.student)
        mock_obj = type("MockObj", (), {"user": self.student})()
        self.assertTrue(self.perm.has_object_permission(req, None, mock_obj))

    def test_denies_non_owner_student(self):
        """Different student cannot access."""
        other = make_student("other_owner@test.com")
        req = make_request(other)
        mock_obj = type("MockObj", (), {"user": self.student})()
        self.assertFalse(self.perm.has_object_permission(req, None, mock_obj))

    def test_denies_professor(self):
        """Professor cannot access student's object."""
        dept = Department.objects.create(department_name="KI7", department_code="KI7")
        prof = make_professor("prof_owner@test.com", dept)
        req = make_request(prof)
        mock_obj = type("MockObj", (), {"user": self.student})()
        self.assertFalse(self.perm.has_object_permission(req, None, mock_obj))

    def test_denies_anonymous(self):
        """Anonymous user cannot access."""
        req = make_request(AnonymousUser())
        mock_obj = type("MockObj", (), {"user": self.student})()
        self.assertFalse(self.perm.has_object_permission(req, None, mock_obj))

    def test_denies_when_obj_has_no_user(self):
        """Object without 'user' attribute is denied."""
        req = make_request(self.student)
        mock_obj = type("MockObj", (), {})()
        self.assertFalse(self.perm.has_object_permission(req, None, mock_obj))

    def test_has_permission_grants_authenticated(self):
        """has_permission returns True for any authenticated user."""
        self.assertTrue(self.perm.has_permission(make_request(self.student), None))

    def test_has_permission_denies_anonymous(self):
        """has_permission returns False for anonymous."""
        self.assertFalse(self.perm.has_permission(make_request(AnonymousUser()), None))
