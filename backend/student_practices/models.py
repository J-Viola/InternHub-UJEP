import logging
import random

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import OneToOneRel
from django_enumfield import enum

from practices.models import ProgressStatus
from student_practices.messages import StudentPracticeMessages
from users.models import ApprovalStatus

logger = logging.getLogger(__name__)


class EmployerInvitationStatus(enum.Enum):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2
    CANCELLED = 3


class EmployerInvitation(models.Model):
    invitation_id = models.AutoField(primary_key=True)
    employer = models.ForeignKey(
        "users.EmployerProfile",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    user = models.ForeignKey(
        "users.StudentUser",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="employer_invitations",
    )
    practice = models.ForeignKey(
        "practices.Practice",
        models.CASCADE,
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


class DocumentType(enum.Enum):
    CONTRACT = 0
    CONTENT = 1
    FEEDBACK = 2


class DocumentStatus(enum.Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    document = models.FileField(
        upload_to="documents", blank=True, null=True, db_index=True
    )
    uploaded_at = models.DateTimeField(blank=True, null=True)
    document_type = enum.EnumField(DocumentType)
    status = enum.EnumField(DocumentStatus, default=DocumentStatus.PENDING)
    review_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "uploaded_documents"

    def __str__(self):
        return self.document.name or super().__str__()

    @property
    def student_practice(self):
        for rel in self._meta.get_fields():
            # Check by name to avoid reference issues before class definition
            if (
                isinstance(rel, OneToOneRel)
                and rel.related_model.__name__ == "StudentPractice"
            ):
                related_object = getattr(self, rel.get_accessor_name(), None)
                if related_object is not None:
                    return related_object
        return None

    def user_has_permission(self, user):
        """
        Centralized permission check for document access.
        """
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        sp = self.student_practice
        if not sp:
            # If document is not linked to any student practice,
            # we might need additional logic here for other types of documents.
            return False

        # Lazy imports to avoid circular dependencies
        from users.models import (
            DepartmentRole,
            OrganizationUser,
            ProfessorUser,
            StudentUser,
            UserSubjectType,
        )

        # 1. Student access (must be the owner)
        if isinstance(user, StudentUser):
            return sp.user_id == user.user_id

        # 2. Professor / Department Head access
        if isinstance(user, ProfessorUser):
            subject = sp.practice.subject
            # Check if professor is assigned to the subject
            if subject.user_subjects.filter(
                user=user, role=UserSubjectType.Professor
            ).exists():
                return True
            # Check if professor is head of department
            if (
                user.department_role == DepartmentRole.HEAD
                and user.department_id == subject.department_id
            ):
                return True

        # 3. Organization access
        if isinstance(user, OrganizationUser):
            # Check if user belongs to the employer organization of the practice
            return sp.practice.employer_id == user.employer_profile_id

        return False


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
        file_path = settings.MEDIA_ROOT / "default_documents" / file_name

        if not file_path.exists():
            logger.warning("Default document %s not found.", file_path)
            return None

        try:
            from django.utils import timezone

            with open(file_path, "rb") as f:
                document_file = File(f)
                document_file.name = f"default_{DocumentHelper.create_name_for_document(document_type, user_id, file_name)}"
                document = UploadedDocument(
                    document_type=document_type,
                    document=document_file,
                    uploaded_at=timezone.now(),
                )
                document.save()
                return document
        except Exception as e:
            logger.error("Error creating default document: %s", str(e))
            return None

    @staticmethod
    def create_name_for_document(
        document_type: DocumentType, user_id: int, file_name: str
    ):
        import os
        import uuid

        from django.utils import timezone

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

        # Sanitize original file name to prevent path traversal
        safe_file_name = os.path.basename(file_name)
        ext = (
            safe_file_name.rsplit(".", 1)[-1].lower()
            if "." in safe_file_name
            else "docx"
        )

        unique_suffix = uuid.uuid4().hex[:6]
        return (
            f"{document_type.name.lower()}_{user_id}_{timestamp}_{unique_suffix}.{ext}"
        )

    @staticmethod
    def assign_default_documents(student_practice):
        """
        Explicitly generates and assigns default documents to a StudentPractice instance.
        """
        try:
            user_id = student_practice.user.id
        except (AttributeError, ValueError, models.ObjectDoesNotExist):
            user_id = random.randint(0, 99999999)

        if not student_practice.contract_document:
            student_practice.contract_document = DocumentHelper.create_default_document(
                DocumentType.CONTRACT, user_id
            )
        if not student_practice.content_document:
            student_practice.content_document = DocumentHelper.create_default_document(
                DocumentType.CONTENT, user_id
            )
        if not student_practice.feedback_document:
            student_practice.feedback_document = DocumentHelper.create_default_document(
                DocumentType.FEEDBACK, user_id
            )

        student_practice.save()


def validate_contract_document_type(value):
    if value and value.document_type != DocumentType.CONTRACT:
        raise ValidationError(StudentPracticeMessages.CONTRACT_DOC_REQUIRED)


def validate_feedback_document_type(value):
    if value and value.document_type != DocumentType.FEEDBACK:
        raise ValidationError(StudentPracticeMessages.FEEDBACK_DOC_REQUIRED)


def validate_content_document_type(value):
    if value and value.document_type != DocumentType.CONTENT:
        raise ValidationError(StudentPracticeMessages.CONTENT_DOC_REQUIRED)


class StudentPractice(models.Model):
    student_practice_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        "users.StudentUser",
        models.CASCADE,
        blank=True,
        null=True,
        related_name="student_practices",
    )
    practice = models.ForeignKey(
        "practices.Practice",
        models.CASCADE,
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
        "users.StagUser",
        models.SET_NULL,
        related_name="cancelled_student_practices",
        blank=True,
        null=True,
    )
    year = models.IntegerField(blank=True, null=True)
    contract_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_contract",
        limit_choices_to={"document_type": DocumentType.CONTRACT},
        validators=[validate_contract_document_type],
        null=True,
    )
    content_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_content",
        limit_choices_to={"document_type": DocumentType.CONTENT},
        validators=[validate_content_document_type],
        null=True,
    )
    feedback_document = models.OneToOneField(
        UploadedDocument,
        models.CASCADE,
        related_name="student_practice_feedback",
        limit_choices_to={"document_type": DocumentType.FEEDBACK},
        validators=[validate_feedback_document_type],
        null=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    school_approved = models.BooleanField(default=False)
    employer_approved = models.BooleanField(default=False)

    class Meta:
        db_table = "student_practices"
        unique_together = (("user", "practice"),)

    def __str__(self):
        return f"{self.user} - {self.practice} (status: {self.approval_status})"

    @property
    def workflow_status(self):
        if self.approval_status == ApprovalStatus.REJECTED:
            return "REJECTED"
        if self.approval_status == ApprovalStatus.PENDING:
            return "PENDING"

        # Approved, so look at progress_status
        if self.progress_status == ProgressStatus.IN_PROGRESS:
            return "IN_PROGRESS"
        if self.progress_status == ProgressStatus.COMPLETED:
            return "COMPLETED"
        if self.progress_status == ProgressStatus.CANCELLED:
            return "CANCELLED"

        return "APPROVED"  # Approved but not started

    @property
    def workflow_status_label(self):
        labels = {
            "REJECTED": "REJECTED",
            "PENDING": "PENDING",
            "APPROVED": "APPROVED",
            "IN_PROGRESS": "IN_PROGRESS",
            "COMPLETED": "COMPLETED",
            "CANCELLED": "CANCELLED",
        }
        return labels.get(self.workflow_status, "UNKNOWN_STATUS")
