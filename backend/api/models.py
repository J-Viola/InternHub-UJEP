# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or
# field names.
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from polymorphic.models import PolymorphicManager, PolymorphicModel


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
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class Status(models.Model):
    status_id = models.AutoField(primary_key=True)
    status_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    status_name = models.CharField(max_length=100, blank=True, null=True)
    status_category = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "status"


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "role"


class StagRole(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.CharField(unique=True, blank=False, null=False)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "stagrole"


class OrganizationRole(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.CharField(unique=True, blank=False, null=False)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "organizationrole"


class EmployerProfile(models.Model):
    employer_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    ico = models.CharField(unique=True, max_length=15, blank=True, null=True)
    dic = models.CharField(unique=True, max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    zip_code = models.IntegerField(blank=True, null=True)
    company_profile = models.TextField(blank=True, null=True)
    approval_status = models.ForeignKey(Status, models.DO_NOTHING, blank=True, null=True)
    logo = models.ImageField(blank=True, null=True)

    class Meta:
        db_table = "employerprofile"


class User(PolymorphicModel, AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    username = models.CharField(unique=True, max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    title_before = models.CharField(max_length=50, blank=True, null=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    title_after = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    activated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"
        swappable = "AUTH_USER_MODEL"

    @property
    def id(self):
        return self.user_id

    @property
    def role(self):
        return None


class OrganizationUser(User):
    employer_profile = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True)
    organization_role = models.ForeignKey(OrganizationRole, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "organizationuser"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def role(self):
        return self.organization_role.role


# Role: student, vedení katedry, vedoucí předmětu
class StagUser(User):
    profile_picture = models.TextField(blank=True, null=True)
    field_of_study = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.IntegerField(blank=True, null=True)
    stag_f_number = models.IntegerField(unique=True, blank=True, null=True)
    resume = models.TextField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=100, blank=True, null=True)
    street_number = models.CharField(max_length=10, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    stag_role = models.ForeignKey(StagRole, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "staguser"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def role(self):
        return self.stag_role.role


class ActionLog(models.Model):
    action_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    action_type = models.CharField(max_length=50, blank=True, null=True)
    object_type = models.CharField(max_length=50, blank=True, null=True)
    object_id = models.IntegerField(blank=True, null=True)
    action_description = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "actionlog"


class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(unique=True, max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "department"


class DepartmentUserRole(models.Model):
    id = models.AutoField(primary_key=True)
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True)
    role = models.ForeignKey(Role, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "departmentuserrole"
        unique_together = (("department", "user", "role"),)


class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True)
    subject_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    subject_name = models.CharField(max_length=100, blank=True, null=True)
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True)
    hours_required = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "subject"


class EmployerInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(OrganizationUser, models.DO_NOTHING, blank=True, null=True)
    practice = models.ForeignKey("Practice", models.DO_NOTHING, blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    status = models.ForeignKey(Status, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "employerinvitation"


class PracticeType(models.Model):
    practice_type_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100, blank=True, null=True)
    coefficient = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = "practicetype"


class Practice(models.Model):
    practice_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True)
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    available_positions = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.ForeignKey(Status, models.DO_NOTHING, blank=True, null=True)
    approval_status = models.ForeignKey(
        Status,
        models.DO_NOTHING,
        related_name="practice_approval_status_set",
        blank=True,
        null=True,
    )
    contact_user = models.ForeignKey(OrganizationUser, models.DO_NOTHING, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    image_base64 = models.TextField(blank=True, null=True)
    practice_type = models.ForeignKey(PracticeType, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "practice"


class PracticeUser(models.Model):
    id = models.AutoField(primary_key=True)
    practice = models.ForeignKey(Practice, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "practiceuser"
        unique_together = (("practice", "user"),)


class StudentPractice(models.Model):
    student_practice_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True)
    practice = models.ForeignKey(Practice, models.DO_NOTHING, blank=True, null=True)
    application_date = models.DateField(blank=True, null=True)
    approval_status = models.ForeignKey(Status, models.DO_NOTHING, blank=True, null=True)
    progress_status = models.ForeignKey(
        Status,
        models.DO_NOTHING,
        related_name="studentpractice_progress_status_set",
        blank=True,
        null=True,
    )
    hours_completed = models.IntegerField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by_user = models.ForeignKey(
        StagUser,
        models.DO_NOTHING,
        related_name="studentpractice_cancelled_by_user_set",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "studentpractice"
        unique_together = (("user", "practice"),)


class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    practice = models.ForeignKey(Practice, models.DO_NOTHING, blank=True, null=True)
    document_name = models.CharField(max_length=100, blank=True, null=True)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    document_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "uploadeddocument"


class UserSubject(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True)
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "usersubject"
        unique_together = (("user", "subject"),)
