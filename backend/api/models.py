# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or
# field names.
import datetime
import hashlib
import random

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.files import File
from django.db import models
from django.db.models import OneToOneRel
from django_enumfield import enum
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


class ApprovalStatus(enum.Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class EmployerInvitationStatus(enum.Enum):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2
    CANCELLED = 3


class ProgressStatus(enum.Enum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.role_name or super().__str__()


class StagRole(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.CharField(unique=True, blank=False, null=False)
    role_name = models.CharField(unique=True, max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "stag_roles"

    def __str__(self):
        return self.role_name or self.role or super().__str__()


class EmployerProfile(models.Model):
    employer_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=100, blank=True, default="")
    ico = models.CharField(unique=True, max_length=15, blank=True, default="")
    dic = models.CharField(unique=True, max_length=15, blank=True, default="")
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
    username = models.CharField(unique=True, max_length=150, blank=True, default="")
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
        models.DO_NOTHING,
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
    stag_role = models.ForeignKey(StagRole, models.DO_NOTHING, blank=True, null=True, related_name="stag_users")

    class Meta:
        db_table = "stag_users"

    def __str__(self):
        return self.stag_role.role

    @property
    def role(self):
        return self.stag_role.role


class StudentUser(StagUser):
    profile_picture = models.TextField(blank=True, default="")
    os_cislo = models.CharField(unique=True, max_length=64, blank=True, default="")
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
    practices = models.ManyToManyField("Practice", through="StudentPractice", related_name="student_users")

    class Meta:
        db_table = "student_users"


class DepartmentRole(enum.Enum):
    TEACHER = 0
    HEAD = 1


class ProfessorUser(StagUser):
    ucit_idno = models.CharField(unique=True, max_length=64, blank=True, default="")
    department = models.ForeignKey(
        "Department",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="professor_users",
    )
    department_role = enum.EnumField(DepartmentRole, blank=True, null=True)

    class Meta:
        db_table = "professor_users"


class ActionLog(models.Model):
    action_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True, related_name="action_logs")
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


class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(unique=True, max_length=100)
    department_code = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "departments"

    def __str__(self):
        return f"{self.department_name} ({self.department_code})"


class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True)
    subject_code = models.CharField(unique=True, max_length=50, blank=True, default="")
    subject_name = models.CharField(max_length=100, blank=True, default="")
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True, related_name="subjects")
    hours_required = models.IntegerField(blank=True, null=True)
    subject_manager = models.ForeignKey(
        "ProfessorUser",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_subjects",
    )

    class Meta:
        db_table = "subjects"

    def __str__(self):
        return self.subject_name or self.subject_code or super().__str__()


class EmployerInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(
        EmployerProfile,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    user = models.ForeignKey(
        StudentUser,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    practice = models.ForeignKey(
        "Practice",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    submission_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    message = models.TextField(blank=True, default="")
    status = enum.EnumField(EmployerInvitationStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employer_invitations"

    def __str__(self):
        return f"Invitation {self.invitation_id} for {self.user} to {self.practice}"


class Practice(models.Model):
    practice_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(
        EmployerProfile,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="practices",
    )
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True, related_name="practices")
    title = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    responsibilities = models.TextField(blank=True, default="")
    available_positions = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    progress_status = enum.EnumField(ProgressStatus)
    approval_status = enum.EnumField(ApprovalStatus)
    contact_user = models.ForeignKey(
        OrganizationUser,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="practices",
    )
    is_active = models.BooleanField(blank=True, null=True)
    image_base64 = models.TextField(blank=True, default="")
    # image = models.ImageField(upload_to=settings.STORAGE_URL + "images/practices", blank=True, null=True)
    coefficient = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "practices"

    def __str__(self):
        return self.title or super().__str__()


class DocumentType(enum.Enum):
    CONTRACT = 0
    CONTENT = 1
    FEEDBACK = 2


class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    document = models.FileField(upload_to=settings.STORAGE_URL + "documents", blank=True, null=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    document_type = enum.EnumField(DocumentType)

    class Meta:
        db_table = "uploaded_documents"

    def __str__(self):
        return self.document.name or super().__str__()

    @property
    def student_practice(self):
        """Vrátí StudentPractice nezávisle na tom jaký typ dokumentu to je."""
        for rel in self._meta.get_fields():
            if isinstance(rel, OneToOneRel) and rel.related_model is StudentPractice:
                related_object = getattr(self, rel.get_accessor_name(), None)
                if related_object is not None:
                    return related_object
        return None


class StudentPractice(models.Model):
    student_practice_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        StudentUser,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="student_practices",
    )
    practice = models.ForeignKey(
        Practice,
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="student_practices",
    )
    application_date = models.DateField(blank=True, null=True)
    approval_status = enum.EnumField(ApprovalStatus)
    progress_status = enum.EnumField(ProgressStatus)
    hours_completed = models.IntegerField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by_user = models.ForeignKey(
        StagUser,
        models.DO_NOTHING,
        related_name="cancelled_student_practices",
        blank=True,
        null=True,
    )
    year = models.IntegerField(blank=True, null=True)
    contract_document = models.OneToOneField(
        UploadedDocument,
        models.DO_NOTHING,
        related_name="student_practice_contract",
        limit_choices_to={"document_type": DocumentType.CONTRACT},
        validators=[],
        null=True,
    )
    content_document = models.OneToOneField(
        UploadedDocument,
        models.DO_NOTHING,
        related_name="student_practice_content",
        limit_choices_to={"document_type": DocumentType.CONTENT},
        validators=[],
        null=True,
    )
    feedback_document = models.OneToOneField(
        UploadedDocument,
        models.DO_NOTHING,
        related_name="student_practice_feedback",
        limit_choices_to={"document_type": DocumentType.FEEDBACK},
        validators=[],
        null=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "student_practices"
        unique_together = (("user", "practice"),)

    def __str__(self):
        return f"{self.user} - {self.practice} (status: {self.approval_status})"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk is None:
            user_id = self.user.id if self.user is not None else random.randint(0, 99999999)
            self.contract_document = DocumentHelper.create_default_document(DocumentType.CONTRACT, user_id)
            self.content_document = DocumentHelper.create_default_document(DocumentType.CONTENT, user_id)
            self.feedback_document = DocumentHelper.create_default_document(DocumentType.FEEDBACK, user_id)

    @staticmethod
    def validate_contract_document_type(value):
        from django.core.exceptions import ValidationError

        if value and value.document_type != DocumentType.CONTRACT:
            raise ValidationError("Document must be of type CONTRACT")

    @staticmethod
    def validate_feedback_document_type(value):
        from django.core.exceptions import ValidationError

        if value and value.document_type != DocumentType.FEEDBACK:
            raise ValidationError("Document must be of type FEEDBACK")

    @staticmethod
    def validate_content_document_type(value):
        from django.core.exceptions import ValidationError

        if value and value.document_type != DocumentType.CONTENT:
            raise ValidationError("Document must be of type CONTENT")


class UserSubjectType(enum.Enum):
    Student = 0
    Professor = 1


class UserSubject(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True, related_name="user_subjects")
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True, related_name="user_subjects")
    role = enum.EnumField(UserSubjectType)

    class Meta:
        db_table = "user_subjects"
        unique_together = (("user", "subject"),)

    def __str__(self):
        return f"{self.user} - {self.subject} ({self.role})"


class DocumentHelper:
    DOCUMENT_FILES = {
        DocumentType.CONTRACT: "default_contract.docx",
        DocumentType.FEEDBACK: "default_feedback.docx",
        DocumentType.CONTENT: "default_content.docx",
    }

    @staticmethod
    def create_default_document(document_type: DocumentType, user_id: int):
        file_name = DocumentHelper.DOCUMENT_FILES.get(document_type)
        if not file_name:
            raise ValueError(f"Unsupported document type: {document_type}")

        file_path = f"{settings.BASE_DIR}/storage/default_documents/{file_name}"
        document_file = File(open(file_path, "rb"))
        document_file.name = f"default_{DocumentHelper.create_name_for_document(document_type, user_id, document_file.name)}"

        document = UploadedDocument(
            document_type=document_type,
            document=document_file,
            uploaded_at=datetime.datetime.now(datetime.UTC),
        )
        document.save()
        return document

    @staticmethod
    def create_name_for_document(document_type: DocumentType, user_id: int, file_name: str):
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S")
        ext = file_name.rsplit(".", 1)[-1].lower()
        user_id_hash = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
        return f"{document_type.name.lower()}_{user_id_hash}_{timestamp}.{ext}"
