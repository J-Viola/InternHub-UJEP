from datetime import date

from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from api.helpers import FormattedDateField
from api.validators import validate_file_size
from practices.messages import PracticeMessages
from practices.models import (
    REGION_CHOICES,
    ApplicationClosureReason,
    Practice,
    PracticeWorkflowState,
    ProgressStatus,
)
from practices.utils import calculate_end_date
from student_practices.serializers import StudentPracticeStatusSerializer
from subject.models import Subject
from subject.serializers import SubjectSerializer
from users.models import ApprovalStatus, EmployerProfile, User
from users.serializers import EmployerProfileSerializer

EXTERNAL_DETAILS_REQUIRED = "Nahrání dokumentu s detaily praxe je povinné"


class OrganizationPracticeSerializer(serializers.ModelSerializer):
    """Serializer pro zobrazení praxí organizace"""

    contact_user_full_name = serializers.CharField(source="contact_user.full_name", read_only=True)
    created_at = FormattedDateField(read_only=True)

    # Statistiky studentů
    approved_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "title",
            "contact_user_full_name",
            "created_at",
            "available_positions",
            "approved_count",
            "pending_count",
            "approval_status",
            "workflow_state",
            "workflow_status_label",
            "progress_status",
            "mentor_name",
            "contact_email",
            "region",
        ]

    def get_approved_count(self, obj):
        if hasattr(obj, "approved_count"):
            return obj.approved_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.APPROVED).count()

    def get_pending_count(self, obj):
        if hasattr(obj, "pending_count"):
            return obj.pending_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.PENDING).count()


class PracticeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model Practice
    """

    employer = EmployerProfileSerializer(read_only=True)
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployerProfile.objects.all(),
        source="employer",
        write_only=True,
        required=True,
    )

    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), source="subject", write_only=True, required=True)

    contact_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    contact_user_info = serializers.SerializerMethodField(read_only=True)
    external_employer = serializers.PrimaryKeyRelatedField(read_only=True)
    external_employer_info = serializers.SerializerMethodField()
    student_practice_status = serializers.SerializerMethodField(read_only=True)
    student_practice_documents = serializers.SerializerMethodField(read_only=True)
    start_date = FormattedDateField()
    end_date = FormattedDateField(required=False)
    available_positions = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=1000)
    coefficient = serializers.FloatField(
        read_only=True, help_text="TODO: DEPRECATED — field bude odstraněn v budoucí verzi. Použijte Subject.min_hours (480 default)."
    )
    title = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField(required=True, allow_blank=False)
    responsibilities = serializers.CharField(required=True, allow_blank=False)
    # povinná pole nabídky — mentor + kontaktní e-mail.
    mentor_name = serializers.CharField(required=True, allow_blank=False, help_text="Jméno mentora praxe")
    contact_email = serializers.EmailField(required=True, allow_blank=False, help_text="Kontaktní e-mail nabídky")
    region = serializers.ChoiceField(
        choices=REGION_CHOICES, required=False, allow_blank=True, default="", help_text="Kraj, kde se praxe koná"
    )
    workflow_status_label = serializers.CharField(read_only=True)
    # počty schválených / čekajících přihlášek (z anotací querysetu).
    approved_applications = serializers.SerializerMethodField()
    pending_applications = serializers.SerializerMethodField()

    def get_approved_applications(self, obj):
        if hasattr(obj, "approved_count"):
            return obj.approved_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.APPROVED).count()

    def get_pending_applications(self, obj):
        if hasattr(obj, "pending_count"):
            return obj.pending_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.PENDING).count()

    def get_contact_user_info(self, obj):
        if obj.contact_user:
            return {
                "user_id": obj.contact_user.user_id,
                "username": obj.contact_user.username,
                "first_name": obj.contact_user.first_name,
                "last_name": obj.contact_user.last_name,
                "email": obj.contact_user.email,
                "phone": obj.contact_user.phone,
            }
        return None

    def get_external_employer_info(self, obj):
        if obj.external_employer:
            return {"id": obj.external_employer.id, "name": obj.external_employer.name}
        return None

    def get_student_practice_documents(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        from users.models import StudentUser

        if not isinstance(request.user, StudentUser):
            return []

        user_id = request.user.id
        if hasattr(obj, "_current_user_practices"):
            practices = [sp for sp in obj._current_user_practices if sp.user_id == user_id]
        else:
            practices = obj.student_practices.filter(user_id=user_id)

        student_practice_documents = []
        for sp in practices:
            if sp.approval_status != ApprovalStatus.APPROVED:
                continue
            if sp.contract_document_id:
                student_practice_documents.append(self._document_payload(sp.contract_document, "contract"))
            if sp.content_document_id:
                student_practice_documents.append(self._document_payload(sp.content_document, "content"))
            if sp.feedback_document_id:
                student_practice_documents.append(self._document_payload(sp.feedback_document, "feedback"))

        return student_practice_documents

    @staticmethod
    def _document_payload(document, doc_type):
        """dokument payload doplněn o uploaded_at (ISO) a late_submission ."""
        return {
            "id": document.document_id,
            "type": doc_type,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "late_submission": bool(document.late_submission),
        }

    def get_student_practice_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        from users.models import StudentUser

        if not isinstance(request.user, StudentUser):
            return None

        user_id = request.user.id
        if hasattr(obj, "_current_user_practices"):
            practices = [sp for sp in obj._current_user_practices if sp.user_id == user_id]
        else:
            practices = obj.student_practices.filter(user_id=user_id)

        for sp in practices:
            return StudentPracticeStatusSerializer(sp).data

        return None

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "employer",
            "employer_id",
            "subject",
            "subject_id",
            "title",
            "description",
            "responsibilities",
            "available_positions",
            "start_date",
            "end_date",
            "progress_status",
            "approval_status",
            "workflow_state",
            "contact_user",
            "contact_user_info",
            "student_practice_documents",
            "is_active",
            "image_base64",
            "coefficient",
            "student_practice_status",
            "is_external",
            "external_employer",
            "external_employer_info",
            "skills",
            "city",
            "mentor_name",
            "contact_email",
            "region",
            "workflow_status_label",
            "approved_applications",
            "pending_applications",
        ]
        read_only_fields = ["practice_id", "is_active", "workflow_state", "approval_status", "progress_status"]

    def validate(self, data):
        """
        Zkontroluje, zda end_date není před start_date, a že start_date >= dnešek.
        """
        start = data.get("start_date")
        end = data.get("end_date")

        if start and start < date.today():
            raise serializers.ValidationError(PracticeMessages.DATE_IN_PAST)

        if start and end and end < start:
            raise serializers.ValidationError(PracticeMessages.END_DATE_BEFORE_START)

        return data

    def create(self, validated_data):
        validated_data.setdefault("is_active", True)
        validated_data.setdefault("progress_status", ProgressStatus.NOT_STARTED)
        validated_data.setdefault("approval_status", ApprovalStatus.PENDING)
        validated_data.setdefault("workflow_state", PracticeWorkflowState.PENDING_CONTENT_APPROVAL)

        start_date = validated_data.get("start_date")
        subject = validated_data.get("subject")
        if start_date and subject:
            min_hours = getattr(subject, "min_hours", 480)
            validated_data["end_date"] = calculate_end_date(start_date, min_hours=min_hours)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class RunningPracticeSerializer(serializers.ModelSerializer):
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployerProfile.objects.all(),
        source="employer",
        write_only=True,
        required=True,
    )
    subject_code = serializers.CharField(source="subject.subject_code", read_only=True)
    contact_user_name = serializers.CharField(source="contact_user.full_name", read_only=True)
    # Add student practice related fields
    student_count = serializers.SerializerMethodField()
    approved_student_count = serializers.SerializerMethodField()
    pending_student_count = serializers.SerializerMethodField()
    start_date = FormattedDateField()
    end_date = FormattedDateField()

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "employer_id",
            "subject_code",
            "title",
            "start_date",
            "end_date",
            "contact_user_name",
            "student_count",
            "approved_student_count",
            "pending_student_count",
            "available_positions",
            "skills",
        ]
        read_only_fields = ["practice_id", "is_active", "workflow_state", "approval_status", "progress_status"]

    def get_contact_user_info(self, obj):
        if obj.contact_user:
            return {
                "user_id": obj.contact_user.user_id,
                "username": obj.contact_user.username,
                "email": obj.contact_user.email,
                "full_name": obj.contact_user.full_name,
            }
        return None

    def get_student_count(self, obj):
        if hasattr(obj, "total_student_count"):
            return obj.total_student_count
        return obj.student_practices.count()

    def get_approved_student_count(self, obj):
        if hasattr(obj, "approved_count"):
            return obj.approved_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.APPROVED).count()

    def get_pending_student_count(self, obj):
        if hasattr(obj, "pending_count"):
            return obj.pending_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.PENDING).count()

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(PracticeMessages.END_DATE_BEFORE_START)
        if start and start < date.today():
            raise serializers.ValidationError(PracticeMessages.DATE_IN_PAST)
        return data

    def create(self, validated_data):
        if "is_active" not in validated_data:
            validated_data["is_active"] = True
        if "progress_status" not in validated_data:
            validated_data["progress_status"] = ProgressStatus.NOT_STARTED
        if "approval_status" not in validated_data:
            validated_data["approval_status"] = ApprovalStatus.PENDING
        if "workflow_state" not in validated_data:
            validated_data["workflow_state"] = PracticeWorkflowState.PENDING_CONTENT_APPROVAL
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PracticeApprovalSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.subject_name", read_only=True)
    subject_code = serializers.CharField(source="subject.subject_code", read_only=True)
    department_name = serializers.CharField(source="subject.department.department_name", read_only=True)
    contact_user_full_name = serializers.CharField(source="contact_user.full_name", read_only=True)
    contact_user_email = serializers.CharField(source="contact_user.email", read_only=True)
    created_at = FormattedDateField(read_only=True)

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "title",
            "created_at",
            "subject_name",
            "subject_code",
            "department_name",
            "contact_user_id",
            "contact_user_email",
            "contact_user_full_name",
            "approval_status",
        ]


class PracticeApprovalStatusSerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(
        choices=[(choice[1], choice[1]) for choice in ApprovalStatus.choices() if choice[0] != ApprovalStatus.PENDING],
        help_text="Status schválení praxe (pouze pro schválení nebo zamítnutí)",
    )


class EndDateRequestSerializer(serializers.Serializer):
    start_date = FormattedDateField(help_text="Start date")
    coefficient = serializers.FloatField(
        help_text="DEPRECATED — field bude odstraněn v budoucí verzi. Použijte min_hours (480 default).",
        min_value=0.1,
        max_value=10.0,
        required=False,
    )
    min_hours = serializers.IntegerField(
        help_text="Total minimum practice hours (from Subject.min_hours)",
        min_value=0,
        required=False,
    )


class EndDateResponseSerializer(serializers.Serializer):
    end_date = FormattedDateField(help_text="Calculated end date")


class TransitionPracticeSerializer(serializers.Serializer):
    """
    Request serializer pro POST /api/practices/{id}/transition.
    """

    target_state = serializers.ChoiceField(
        choices=[(s.value, s.name) for s in list(PracticeWorkflowState)],
        help_text="Cílový stav workflow (číselná hodnota enumu).",
    )
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Důvod přechodu (nepovinný).")

    def validate(self, data):
        target_state = data.get("target_state")
        if target_state in ("REJECTED", "CONTENT_REJECTED", "DOCUMENTS_REJECTED"):
            if not data.get("reason", "").strip():
                raise serializers.ValidationError({"reason": "Důvod je povinný při zamítnutí nebo vrácení."})
        return data


class CancelPracticeSerializer(serializers.Serializer):
    """Request serializer pro POST /api/practices/{id}/cancel."""

    reason = serializers.CharField(required=True, help_text="Důvod storna (povinný).")


class CloseApplicationsSerializer(serializers.Serializer):
    """
    Request serializer pro POST /api/practices/{id}/close-applications.

    důvod je nepovinný — manuální uzavření vždy zapisuje
    ``closed_reason=ApplicationClosureReason.MANUAL``, hodnota z requestu
    se nebere.
    """

    reason = serializers.ChoiceField(
        choices=[(r.value, r.name) for r in list(ApplicationClosureReason)],
        required=False,
        help_text="Důvod uzávěrky přihlášek (nepovinné — vždy se zapíše MANUAL).",
    )


class ExternalPracticeSerializer(serializers.ModelSerializer):
    """Serializer pro vytvoření mimosystémové praxe (studenti/škola bez registrované firmy)."""

    employer_name = serializers.CharField(required=True, help_text="Název externí organizace.")
    contact_person = serializers.CharField(required=False, allow_blank=True, help_text="Kontaktní osoba v externí organizaci.")
    contact_email = serializers.EmailField(required=False, allow_blank=True, help_text="Kontaktní email externí organizace.")
    ico = serializers.CharField(required=False, allow_blank=True, help_text="IČO externí organizace.")
    address = serializers.CharField(required=False, allow_blank=True, help_text="Adresa externí organizace.")
    contact_phone = serializers.CharField(required=False, allow_blank=True, help_text="Telefonní kontakt externí organizace.")
    start_date = FormattedDateField()
    end_date = FormattedDateField(required=False)
    # povinná příloha s detaily praxe (PDF/DOCX, <= MAX_UPLOAD_SIZE).
    external_details_file = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[FileExtensionValidator(["pdf", "docx"]), validate_file_size],
        help_text="Soubor s detaily mimosystémové praxe (PDF/DOCX, max 10 MB) — povinné.",
    )

    class Meta:
        model = Practice
        fields = [
            "employer_name",
            "contact_person",
            "contact_email",
            "ico",
            "address",
            "contact_phone",
            "external_details_file",
            "subject_id",
            "title",
            "description",
            "responsibilities",
            "available_positions",
            "start_date",
            "end_date",
            "skills",
            "coefficient",
        ]

    def validate(self, data):
        """Check start_date is not in the past, end_date ≥ start_date and file present."""
        start = data.get("start_date")
        end = data.get("end_date")
        if start and start < date.today():
            raise serializers.ValidationError(PracticeMessages.DATE_IN_PAST)
        if start and end and end < start:
            raise serializers.ValidationError(PracticeMessages.END_DATE_BEFORE_START)
        # externí praxe vyžaduje dokument s detaily praxe.
        if not data.get("external_details_file"):
            raise serializers.ValidationError({"external_details_file": EXTERNAL_DETAILS_REQUIRED})
        return data

    def create(self, validated_data):
        from practices.models import ExternalEmployerInfo

        employer_name = validated_data.pop("employer_name")
        contact_person = validated_data.pop("contact_person", "")
        contact_email = validated_data.pop("contact_email", "")
        ico = validated_data.pop("ico", "")
        address = validated_data.pop("address", "")
        contact_phone = validated_data.pop("contact_phone", "")

        # ARES lock enforcement — pokud je profil vytvářející organizace
        # uzamčený (ares_locked=True), přepíšeme employer_name/address hodnotami
        # z ARES (zamčená data profilu) a hodnoty z clientu se ignorují.
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        employer_profile = getattr(user, "employer_profile", None) if user else None
        if employer_profile and employer_profile.ares_locked:
            if employer_profile.company_name:
                employer_name = employer_profile.company_name
            if employer_profile.address:
                address = employer_profile.address

        created_by = self.context["request"].user

        external_info = ExternalEmployerInfo.objects.create(
            name=employer_name,
            ico=ico,
            address=address,
            contact_name=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone,
            created_by=created_by,
        )

        validated_data["is_external"] = True
        validated_data["external_employer"] = external_info
        validated_data["employer"] = None  # externí praxe nemá EmployerProfile
        validated_data.setdefault("is_active", True)
        validated_data.setdefault("workflow_state", PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        validated_data.setdefault("approval_status", ApprovalStatus.PENDING)
        validated_data.setdefault("progress_status", ProgressStatus.NOT_STARTED)

        return super().create(validated_data)
