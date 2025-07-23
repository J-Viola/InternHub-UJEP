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
from datetime import timezone

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
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.role_name or super().__str__()


class StagRole(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.CharField(unique=True, blank=False, null=False)
    role_name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.role_name or self.role or super().__str__()

    class Meta:
        db_table = "stag_roles"


class EmployerProfile(models.Model):
    employer_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    ico = models.CharField(unique=True, max_length=15, blank=True, null=True)
    dic = models.CharField(unique=True, max_length=15, blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    zip_code = models.IntegerField(blank=True, null=True)
    company_profile = models.TextField(blank=True, null=True)
    approval_status = enum.EnumField(ApprovalStatus)
    logo = models.ImageField(upload_to=settings.STORAGE_URL + "images/logos", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name or super().__str__()

    class Meta:
        db_table = "employer_profiles"


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
        return f"{self.title_before or " "} {self.first_name} {self.last_name} {self.title_after or " "}".strip()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class OrganizationRole(enum.Enum):
    OWNER = 0
    INSERTER = 1


class OrganizationUser(User):
    employer_profile = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True, related_name="organization_users")
    organization_role = enum.EnumField(OrganizationRole, blank=True, null=True)

    class Meta:
        db_table = "organization_users"

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def role(self):

        if self.organization_role is not None:
            return self.organization_role.name
        else:
            return None


class StagUser(User):
    stag_role = models.ForeignKey(StagRole, models.DO_NOTHING, blank=True, null=True, related_name="stag_users")

    class Meta:
        db_table = "stag_users"

    @property
    def role(self):
        return self.stag_role.role


class StudentUser(StagUser):
    profile_picture = models.TextField(blank=True, null=True)
    os_cislo = models.CharField(unique=True, max_length=64, blank=True, null=True)
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
    practices = models.ManyToManyField("Practice", through="StudentPractice", related_name="student_users")

    class Meta:
        db_table = "student_users"


class DepartmentRole(enum.Enum):
    TEACHER = 0
    HEAD = 1


class ProfessorUser(StagUser):
    ucit_idno = models.CharField(unique=True, max_length=64, blank=True, null=True)
    department = models.ForeignKey("Department", models.DO_NOTHING, blank=True, null=True, related_name="professor_users")
    department_role = enum.EnumField(DepartmentRole, blank=True, null=True)

    class Meta:
        db_table = "professor_users"


class ActionLog(models.Model):
    action_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True, related_name="action_logs")
    action_type = models.CharField(max_length=50, blank=True, null=True)
    object_type = models.CharField(max_length=50, blank=True, null=True)
    object_id = models.IntegerField(blank=True, null=True)
    action_description = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        user_repr = str(self.user) if self.user else "Unknown"
        return f"[{self.action_date}] {self.action_type} by {user_repr}"

    class Meta:
        db_table = "action_logs"


class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(unique=True, max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.department_name or super().__str__()

    class Meta:
        db_table = "departments"


class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True)
    subject_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    subject_name = models.CharField(max_length=100, blank=True, null=True)
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True, related_name="subjects")
    hours_required = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.subject_name or self.subject_code or super().__str__()

    class Meta:
        db_table = "subjects"


class EmployerInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True, related_name="employer_invitations")
    user = models.ForeignKey(StudentUser, models.DO_NOTHING, blank=True, null=True, related_name="employer_invitations")
    practice = models.ForeignKey("Practice", models.DO_NOTHING, blank=True, null=True, related_name="employer_invitations")
    submission_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    status = enum.EnumField(EmployerInvitationStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invitation {self.invitation_id} for {self.user} to {self.practice}"

    class Meta:
        db_table = "employer_invitations"


class PracticeType(models.Model):
    practice_type_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100, blank=True, null=True)
    coefficient = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name or super().__str__()

    class Meta:
        db_table = "practice_types"


class Practice(models.Model):
    practice_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(EmployerProfile, models.DO_NOTHING, blank=True, null=True, related_name="practices")
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True, related_name="practices")
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    available_positions = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    progress_status = enum.EnumField(ProgressStatus)
    approval_status = enum.EnumField(ApprovalStatus)
    contact_user = models.ForeignKey(OrganizationUser, models.DO_NOTHING, blank=True, null=True, related_name="practices")
    is_active = models.BooleanField(blank=True, null=True)
    image_base64 = models.TextField(blank=True, null=True)
    # image = models.ImageField(upload_to=settings.STORAGE_URL + "images/practices", blank=True, null=True)
    practice_type = models.ForeignKey(PracticeType, models.DO_NOTHING, blank=True, null=True, related_name="practices")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):

        return self.title or super().__str__()

    class Meta:
        db_table = "practices"


class DocumentType(enum.Enum):
    CONTRACT = 0
    CONTENT = 1
    FEEDBACK = 2


class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    document = models.FileField(upload_to=settings.STORAGE_URL + "documents", blank=True, null=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    document_type = enum.EnumField(DocumentType)

    @property
    def student_practice(self):
        """Vrátí StudentPractice nezávisle na tom jaký typ dokumentu to je."""
        for rel in self._meta.get_fields():
            if isinstance(rel, OneToOneRel) and rel.related_model is StudentPractice:
                related_object = getattr(self, rel.get_accessor_name(), None)
                if related_object is not None:
                    return related_object
        return None

    def __str__(self):
        return self.document.name or super().__str__()

    class Meta:
        db_table = "uploaded_documents"


class StudentPractice(models.Model):
    def validate_contract_document_type(document):
        if document and document.contract_document.document_type != DocumentType.CONTRACT:
            from django.core.exceptions import ValidationError

            raise ValidationError("Document must be of type CONTRACT")

    def validate_feedback_document_type(document):
        if document and document.contract_document.document_type != DocumentType.FEEDBACK:
            from django.core.exceptions import ValidationError

            raise ValidationError("Document must be of type CONTENT")

    def validate_content_document_type(document):
        if document and document.contract_document.document_type != DocumentType.CONTENT:
            from django.core.exceptions import ValidationError

            raise ValidationError("Document must be of type FEEDBACK")

    student_practice_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StudentUser, models.DO_NOTHING, blank=True, null=True, related_name="student_practices")
    practice = models.ForeignKey(Practice, models.DO_NOTHING, blank=True, null=True, related_name="student_practices")
    application_date = models.DateField(blank=True, null=True)
    approval_status = enum.EnumField(ApprovalStatus)
    progress_status = enum.EnumField(ProgressStatus)
    hours_completed = models.IntegerField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
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
        validators=[validate_contract_document_type],
    )
    content_document = models.OneToOneField(
        UploadedDocument,
        models.DO_NOTHING,
        related_name="student_practice_content",
        limit_choices_to={"document_type": DocumentType.CONTENT},
        validators=[validate_content_document_type],
    )
    feedback_document = models.OneToOneField(
        UploadedDocument,
        models.DO_NOTHING,
        related_name="student_practice_feedback",
        limit_choices_to={"document_type": DocumentType.FEEDBACK},
        validators=[validate_feedback_document_type],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk is None:
            self.contract_document = DocumentHelper.create_default_document(DocumentType.CONTRACT, self.user.user_id)
            self.content_document = DocumentHelper.create_default_document(DocumentType.CONTENT, self.user.user_id)
            self.feedback_document = DocumentHelper.create_default_document(DocumentType.FEEDBACK, self.user.user_id)

    def __str__(self):
        return f"{self.user} - {self.practice} (status: {self.approval_status})"

    class Meta:
        db_table = "student_practices"
        unique_together = (("user", "practice"),)


class UserSubjectType(enum.Enum):
    Student = 0
    Professor = 1


class UserSubject(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StagUser, models.DO_NOTHING, blank=True, null=True, related_name="user_subjects")
    subject = models.ForeignKey(Subject, models.DO_NOTHING, blank=True, null=True, related_name="user_subjects")
    role = enum.EnumField(UserSubjectType)

    def __str__(self):
        return f"{self.user} - {self.subject} ({self.role})"

    class Meta:
        db_table = "user_subjects"
        unique_together = (("user", "subject"),)


class DocumentHelper:
    @staticmethod
    def create_default_document(document_type: DocumentType, user_id: int):
        if document_type == DocumentType.CONTRACT:
            file_path = f"{settings.BASE_DIR}/storage/default_documents/default_contract.docx"
            document_file = File(open(file_path, "rb"))

        elif document_type == DocumentType.FEEDBACK:
            file_path = f"{settings.BASE_DIR}/storage/default_documents/default_feedback.docx"
            document_file = File(open(file_path, "rb"))
        elif document_type == DocumentType.CONTENT:
            file_path = f"{settings.BASE_DIR}/storage/default_documents/default_content.docx"
            document_file = File(open(file_path, "rb"))
        else:
            raise ValueError(f"Unsupported document type: {document_type}")

        document_file.name = f"default_{DocumentHelper.create_name_for_document(document_type, user_id, document_file.name)}"

        document = UploadedDocument(document_type=document_type, document=document_file, uploaded_at=datetime.datetime.now())
        document.save()
        return document

    @staticmethod
    def create_name_for_document(document_type: DocumentType, user_id: int, file_name: str):
        timestamp = datetime.datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        ext = file_name.rsplit(".", 1)[-1].lower()
        user_id_hash = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
        return f"{document_type.name.lower()}_{user_id_hash}_{timestamp}.{ext}"
