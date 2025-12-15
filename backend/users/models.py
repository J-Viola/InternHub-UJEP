from enum import Enum as PythonEnum

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django_enumfield import enum
from polymorphic.models import PolymorphicManager, PolymorphicModel


class UserType(PythonEnum):
    ADMIN = "admin"
    STAG = "stag"
    ORGANIZATION = "organization"

    def values(self):
        return [member.value for member in self.__class__]


class StagRoleEnum(PythonEnum):
    ST = "st"
    VY = "vy"
    VK = "vk"


class UserManager(PolymorphicManager, BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class ApprovalStatus(enum.Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.role_name or super().__str__()


class StagRole(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.CharField(unique=True, blank=False, null=False)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "stag_roles"

    def __str__(self):
        return self.role_name or self.role or super().__str__()


class EmployerProfile(models.Model):
    employer_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=100, blank=True, default="")
    ico = models.CharField(unique=True, max_length=15, blank=True, null=True)
    dic = models.CharField(unique=True, max_length=15, blank=True, null=True)
    city = models.TextField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    zip_code = models.IntegerField(blank=True, null=True)
    company_profile = models.TextField(blank=True, default="")
    approval_status = enum.EnumField(ApprovalStatus)
    logo = models.ImageField(upload_to=settings.STORAGE_URL + "images/logos", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employer_profiles"

    def __str__(self):
        return self.company_name or super().__str__()


class User(PolymorphicModel, AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    password = models.CharField(max_length=128, blank=True, default="")
    username = models.CharField(unique=True, max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    title_before = models.CharField(max_length=50, blank=True, default="")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    title_after = models.CharField(max_length=50, blank=True, default="")
    phone = models.CharField(max_length=15, blank=True, default="")
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    activated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_joined = models.DateField(blank=True, null=True)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        swappable = "AUTH_USER_MODEL"

    @property
    def id(self):
        return self.user_id

    @property
    def role(self):
        return None

    @property
    def full_name(self):
        return f"{self.title_before or ' '} {self.first_name} {self.last_name} {self.title_after or ' '}".strip()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class OrganizationRole(enum.Enum):
    OWNER = 0
    INSERTER = 1


class OrganizationUser(User):
    employer_profile = models.ForeignKey(
        EmployerProfile,
        models.CASCADE,
        blank=True,
        null=True,
        related_name="organization_users",
    )
    organization_role = enum.EnumField(OrganizationRole, blank=True, null=True)

    class Meta:
        db_table = "organization_users"

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def role(self):
        return self.organization_role.name if self.organization_role is not None else None


class StagUser(User):
    stag_role = models.ForeignKey(StagRole, models.PROTECT, blank=True, null=True, related_name="stag_users")

    class Meta:
        db_table = "stag_users"

    def __str__(self):
        return self.stag_role.role

    @property
    def role(self):
        return self.stag_role.role


class StudentUser(StagUser):
    profile_picture = models.ImageField(upload_to=settings.STORAGE_URL + "images/profiles", blank=True, null=True)
    os_cislo = models.CharField(unique=True, max_length=64, blank=True, null=True)
    field_of_study = models.CharField(max_length=100, blank=True, default="")
    year_of_study = models.IntegerField(blank=True, null=True)
    stag_f_number = models.IntegerField(unique=True, blank=True, null=True)
    resume = models.TextField(blank=True, default="")
    additional_info = models.TextField(blank=True, default="")
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(max_length=100, blank=True, default="")
    street = models.CharField(max_length=100, blank=True, default="")
    street_number = models.CharField(max_length=10, blank=True, default="")
    zip_code = models.CharField(max_length=10, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    specialization = models.CharField(max_length=100, blank=True, default="")
    practices = models.ManyToManyField("practices.Practice", through="student_practices.StudentPractice", related_name="student_users")

    class Meta:
        db_table = "student_users"


class DepartmentRole(enum.Enum):
    TEACHER = 0
    HEAD = 1


class ProfessorUser(StagUser):
    ucit_idno = models.CharField(unique=True, max_length=64, blank=True, null=True)
    department = models.ForeignKey(
        "department.Department",
        models.PROTECT,
        blank=True,
        null=True,
        related_name="professor_users",
    )
    department_role = enum.EnumField(DepartmentRole, blank=True, null=True)

    class Meta:
        db_table = "professor_users"


class ActionLog(models.Model):
    action_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.SET_NULL, blank=True, null=True, related_name="action_logs")
    action_type = models.CharField(max_length=50, blank=True, default="")
    object_type = models.CharField(max_length=50, blank=True, default="")
    object_id = models.IntegerField(blank=True, null=True)
    action_description = models.TextField(blank=True, default="")
    action_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "action_logs"

    def __str__(self):
        user_repr = str(self.user) if self.user else "Unknown"
        return f"[{self.action_date}] {self.action_type} by {user_repr}"


class UserSubjectType(enum.Enum):
    Student = 0
    Professor = 1


class UserSubject(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StagUser, models.CASCADE, blank=True, null=True, related_name="user_subjects")
    subject = models.ForeignKey("subject.Subject", models.CASCADE, blank=True, null=True, related_name="user_subjects")
    role = enum.EnumField(UserSubjectType)

    class Meta:
        db_table = "user_subjects"
        unique_together = (("user", "subject"),)

    def __str__(self):
        return f"{self.user} - {self.subject} ({self.role})"
