from datetime import date

from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from api.helpers import FormattedDateField
from practices.messages import PracticeMessages
from practices.models import Practice
from student_practices.messages import StudentPracticeMessages
from student_practices.models import (
    EmployerInvitation,
    Evaluation,
    StudentPractice,
    StudentPracticeWorkflowState,
    UploadedDocument,
)
from users.models import ActionLog, ApprovalStatus, User


class EmployerInvitationApprovalSerializer(serializers.Serializer):
    invitation_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["accept", "reject"])


class EmployerInvitationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="invitation_id", read_only=True)
    recipient_name = serializers.CharField(source="user.full_name", read_only=True)
    employer_name = serializers.CharField(source="employer.company_name", read_only=True)
    department = serializers.SerializerMethodField()
    project_title = serializers.CharField(source="practice.title", read_only=True)
    recipient_id = serializers.IntegerField(source="user.user_id", read_only=True)

    class Meta:
        model = EmployerInvitation
        fields = [
            "id",
            "invitation_id",
            "recipient_name",
            "employer_name",
            "department",
            "project_title",
            "recipient_id",
            "status",
            "submission_date",
        ]

    def get_department(self, obj):
        # Try to get student's department via subjects
        # This is simplified; student might have multiple departments
        if obj.user and hasattr(obj.user, "user_subjects"):
            subjects = obj.user.user_subjects.filter(role=0).select_related("subject__department")  # Role 0 = Student
            if subjects.exists():
                return subjects.first().subject.department.department_name
        return ""


class CreateInvitationSerializer(serializers.Serializer):
    practice_id = serializers.IntegerField()
    student_ids = serializers.ListField(child=serializers.IntegerField(), max_length=50)


class StudentPracticeSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    start_date = FormattedDateField()
    end_date = FormattedDateField()

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "user",
            "user_info",
            "practice",
            "application_date",
            "approval_status",
            "progress_status",
            "workflow_state",
            "workflow_status",
            "workflow_status_label",
            "rejection_reason",
            "hours_completed",
            "cancellation_reason",
            "year",
            "start_date",
            "end_date",
        ]
        read_only_fields = [
            "student_practice_id",
            "workflow_status",
            "workflow_status_label",
        ]

    def get_user_info(self, obj):
        if obj.user:
            return {
                "user_id": obj.user.user_id,
                "full_name": obj.user.full_name,
                "email": obj.user.email,
            }
        return None


class StudentPracticeWithDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer pro model StudentPractice (původně v api/serializers.py)
    - student_practice_id: primární klíč (read-only)
    - practice: PK praxe (write-only)
    - title: název praxe (read-only)
    - logo: base64 obrázek praxe (read-only)
    - application_date: datum podání (read-only)
    - approval_status: nested Status (read-only)
    - progress_status: nested Status (read-only)
    - hours_completed: počet dokončených hodin
    - cancellation_reason: důvod zrušení
    - cancelled_by: PK uživatele, kdo zrušil (write-only, volitelné) — z CancellationMixin
    - cancelled_by_info: informace o uživateli, který zrušil (read-only)
    """

    practice = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), write_only=True, required=True)
    title = serializers.CharField(source="practice.title", read_only=True)
    logo = serializers.CharField(source="practice.image_base64", read_only=True)

    # cancelled_by z CancellationMixin (přejmenování cancelled_by_user)
    cancelled_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    cancelled_by_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "practice",
            "title",
            "logo",
            "application_date",
            "approval_status",
            "progress_status",
            "workflow_state",
            "rejection_reason",
            "hours_completed",
            "cancellation_reason",
            "cancelled_from_state",
            "cancelled_by",
            "cancelled_by_info",
        ]
        read_only_fields = [
            "student_practice_id",
            "title",
            "logo",
            "application_date",
            "cancelled_from_state",
            "cancelled_by_info",
        ]

    def get_cancelled_by_info(self, obj):
        if obj.cancelled_by:
            return {
                "user_id": obj.cancelled_by.user_id,
                "full_name": obj.cancelled_by.full_name,
            }
        return None

    def validate(self, data):
        """
        Zkontroluje, zda student již není přihlášen na tuto praxi, a že hours_completed >= 0.
        """
        practice = data.get("practice")
        user = self.context["request"].user if "request" in self.context else None
        if user and StudentPractice.objects.filter(practice=practice, user=user).exists():
            raise serializers.ValidationError(PracticeMessages.ALREADY_APPLIED)
        hours = data.get("hours_completed", 0)
        if hours < 0:
            raise serializers.ValidationError(StudentPracticeMessages.NEGATIVE_HOURS)
        return data

    def create(self, validated_data):
        """
        Nastaví výchozí application_date na dnešní datum, pokud není zadáno,
        a výchozí approval_status na 'pending'.
        """
        if "application_date" not in validated_data:
            validated_data["application_date"] = date.today()
        if "approval_status" not in validated_data:
            pending_status = ApprovalStatus.PENDING
            if pending_status:
                validated_data["approval_status"] = pending_status
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ListStudentPracticeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model StudentPractice
    - student_practice_id: primární klíč (read-only)
    - practice_id: PK praxe (read-only)
    - practice_title: název praxe (read-only)
    - application_date: datum podání žádosti (read-only)
    - approval_status: nested Status (read-only)
    - progress_status: nested Status (read-only)
    - hours_completed: počet dokončených hodin
    """

    practice_id = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), required=True)
    practice_title = serializers.CharField(source="practice.title", read_only=True)
    title = serializers.CharField(source="practice.title", read_only=True)
    department_name = serializers.CharField(source="practice.subject.department.department_name", read_only=True)
    application_date = FormattedDateField(read_only=True)
    student_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_id = serializers.IntegerField(source="user.user_id", read_only=True)
    # pro admin list view
    employer_id = serializers.SerializerMethodField()
    employer_name = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    workflow_state = serializers.SerializerMethodField()
    contract_received_date = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    contract_overdue = serializers.BooleanField(read_only=True)
    # Additive (BL-04): pending-vs-rejected storno žádosti (C02-A) pro FE
    cancellation_requested_at = serializers.DateTimeField(read_only=True, allow_null=True)
    cancellation_resolved_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = StudentPractice
        fields = [
            "practice_id",
            "student_practice_id",
            "department_name",
            "student_full_name",
            "user_id",
            "practice_title",
            "title",
            "application_date",
            "approval_status",
            "progress_status",
            "workflow_status",
            "workflow_status_label",
            "workflow_state",
            "contract_received_date",
            "updated_at",
            "contract_overdue",
            "hours_completed",
            "employer_id",
            "employer_name",
            "can_approve",
            "is_cancelled",
            "cancelled_at",
            "cancellation_reason",
            "cancelled_from_state",
            "rejection_reason",
            "cancelled_by_info",
            "cancellation_requested_at",
            "cancellation_resolved_at",
        ]
        read_only_fields = [
            "student_practice_id",
            "practice_title",
            "application_date",
            "workflow_status",
            "workflow_status_label",
            "can_approve",
            "is_cancelled",
            "cancelled_at",
            "cancellation_reason",
            "cancelled_from_state",
            "rejection_reason",
            "cancelled_by_info",
        ]

    def get_employer_id(self, obj):
        return obj.practice.employer.employer_id if obj.practice.employer else None

    def get_employer_name(self, obj):
        return obj.practice.employer.company_name if obj.practice.employer else None

    def get_workflow_state(self, obj):
        return obj.workflow_state.name if obj.workflow_state else None

    def get_contract_received_date(self, obj):
        return obj.contract_received_date.strftime("%d.%m.%Y %H:%M") if obj.contract_received_date else None

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%d.%m.%Y %H:%M") if obj.updated_at else None

    # TODO ME-1: N+1 — can_approve_practice() queries user_subjects per row.
    # Prefetch user.user_subjects in the view's get_queryset or cache subject IDs.
    def get_can_approve(self, obj):
        from .utils import can_approve_practice

        return can_approve_practice(self.context.get("request").user, obj) if "request" in self.context else False

    cancelled_by_info = serializers.SerializerMethodField(read_only=True)

    def get_cancelled_by_info(self, obj):
        if obj.cancelled_by:
            return {
                "user_id": obj.cancelled_by.user_id,
                "full_name": obj.cancelled_by.full_name,
            }
        return None


class StudentPracticeStatusSerializer(serializers.ModelSerializer):
    application_date = FormattedDateField(read_only=True, allow_null=True)
    student_info = serializers.SerializerMethodField()

    class Meta:
        model = StudentPractice
        fields = [
            "application_date",
            "approval_status",
            "progress_status",
            "workflow_status",
            "workflow_status_label",
            "rejection_reason",
            "hours_completed",
            "student_info",
            "school_approved",
            "employer_approved",
        ]

    def get_student_info(self, obj):
        if obj.user:
            return {
                "user_id": obj.user.user_id,
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name,
                "full_name": obj.user.full_name,
                "email": obj.user.email,
                "os_cislo": (obj.user.os_cislo if hasattr(obj.user, "os_cislo") else None),
            }
        return None


class StudentPracticeUploadedDocumentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="document_id", read_only=True)
    type = serializers.IntegerField(source="document_type", read_only=True)

    class Meta:
        model = UploadedDocument
        fields = ["id", "type"]
        read_only_fields = ["id", "type"]


class StudentPracticeCardSerializer(serializers.ModelSerializer):
    employer = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    contact_user_info = serializers.SerializerMethodField()
    student_practice_status = serializers.SerializerMethodField()
    title = serializers.CharField(source="practice.title", read_only=True)
    description = serializers.CharField(source="practice.description", read_only=True)
    responsibilities = serializers.CharField(source="practice.responsibilities", read_only=True)
    available_positions = serializers.IntegerField(source="practice.available_positions", read_only=True)
    start_date = FormattedDateField(source="practice.start_date", read_only=True)
    end_date = FormattedDateField(read_only=True)
    is_active = serializers.BooleanField(source="practice.is_active", read_only=True)
    image_base64 = serializers.CharField(source="practice.image_base64", read_only=True)
    student_practice_documents = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    # Additive (BL-04): pending-vs-rejected storno žádosti (C02-A) + externí
    # praxe (zdrojový stav confirm-contract T2b) pro FE.
    cancellation_requested_at = serializers.DateTimeField(read_only=True, allow_null=True)
    cancellation_resolved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_external = serializers.BooleanField(source="practice.is_external", read_only=True)
    cancelled_from_state = serializers.ReadOnlyField()

    class Meta:
        model = StudentPractice
        fields = [
            "employer",
            "subject",
            "title",
            "description",
            "responsibilities",
            "available_positions",
            "start_date",
            "end_date",
            "progress_status",
            "approval_status",
            "workflow_status",
            "workflow_status_label",
            "contact_user_info",
            "is_active",
            "image_base64",
            "student_practice_status",
            "student_practice_documents",
            "can_approve",
            "is_cancelled",
            "cancelled_at",
            "cancellation_reason",
            "cancelled_from_state",
            "rejection_reason",
            "contract_received_date",
            "updated_at",
            "cancellation_requested_at",
            "cancellation_resolved_at",
            "is_external",
        ]

    def get_can_approve(self, obj):
        from .utils import can_approve_practice

        return can_approve_practice(self.context.get("request").user, obj) if "request" in self.context else False

    def get_contact_user_info(self, obj):
        if obj.practice.contact_user:
            user = obj.practice.contact_user
            return {
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
            }
        return None

    def get_student_practice_status(self, obj):
        return StudentPracticeStatusSerializer(obj).data

    def get_employer(self, obj):
        from users.serializers import EmployerProfileSerializer

        if not obj.practice.employer:
            return None
        return EmployerProfileSerializer(obj.practice.employer).data

    def get_subject(self, obj):
        from subject.serializers import SubjectSerializer

        return SubjectSerializer(obj.practice.subject).data

    # TODO ME-2: Ensure calling views select_related contract_document, content_document, feedback_document
    def get_student_practice_documents(self, obj):
        def _doc_payload(doc, doc_type):
            return {
                "id": doc.document_id,
                "type": doc_type,
                "status": doc.status,
                "review_note": doc.review_note,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "late_submission": doc.late_submission,
            }

        student_practice_documents = []
        if obj.contract_document:
            student_practice_documents.append(_doc_payload(obj.contract_document, "contract"))
        if obj.content_document:
            student_practice_documents.append(_doc_payload(obj.content_document, "content"))
        if obj.feedback_document:
            student_practice_documents.append(_doc_payload(obj.feedback_document, "feedback"))
        return student_practice_documents


# ========================================================================
# Nové serializery pro state machine endpointy
# ========================================================================


class TransitionStudentPracticeSerializer(serializers.Serializer):
    """
    Request serializer pro POST /api/student-practices/{id}/transition.
    """

    target_state = serializers.ChoiceField(
        choices=[(s.value, s.name) for s in list(StudentPracticeWorkflowState)],
        help_text="Cílový stav workflow (číselná hodnota enumu).",
    )
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Důvod přechodu (nepovinný).")

    def validate(self, data):
        target_state = data.get("target_state")
        if target_state in ("REJECTED", "CONTENT_REJECTED", "DOCUMENTS_REJECTED"):
            if not data.get("reason", "").strip():
                raise serializers.ValidationError({"reason": "Důvod je povinný při zamítnutí nebo vrácení."})
        return data


class CancelStudentPracticeSerializer(serializers.Serializer):
    """
    Request serializer pro POST /api/student-practices/{id}/cancel.
    """

    reason = serializers.CharField(required=True, help_text="Důvod storna (povinný).")


class ActionLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")

    class Meta:
        model = ActionLog
        fields = [
            "action_id",
            "user_name",
            "action_type",
            "action_description",
            "action_date",
        ]


class EvaluationSerializer(serializers.ModelSerializer):
    student_practice_id = serializers.IntegerField(write_only=True)
    evaluated_by_name = serializers.CharField(source="evaluated_by.full_name", read_only=True)
    pdf_file = serializers.FileField(required=False, allow_null=True, validators=[FileExtensionValidator(allowed_extensions=["pdf"])])

    class Meta:
        model = Evaluation
        fields = [
            "evaluation_id",
            "student_practice_id",
            "expertise_rating",
            "expertise_comment",
            "communication_rating",
            "communication_comment",
            "initiative_rating",
            "initiative_comment",
            "overall_comment",
            "pdf_file",
            "pdf_protokol",
            "evaluated_by",
            "evaluated_by_name",
            "evaluated_at",
        ]
        read_only_fields = ["evaluation_id", "evaluated_by", "evaluated_by_name", "evaluated_at", "pdf_protokol"]

    def validate_student_practice_id(self, value):
        # BLOCKER-2: relace je neměnná — update nesmí převalidovat evaluaci
        # na cizí/převzatou přihlášku (autorizace probe probíhá jen pro
        # stávající objekt, nikoli pro nový cílový SP).
        if self.instance is not None and value != self.instance.student_practice_id:
            raise serializers.ValidationError("StudentPractice u existující evaluace nelze měnit.")
        return value

    def validate(self, data):
        # PDF is required when SP is in ENDED or COMPLETED state
        sp_id = data.get("student_practice_id") or (self.instance.student_practice_id if self.instance else None)
        if sp_id:
            from student_practices.models import StudentPractice, StudentPracticeWorkflowState

            try:
                sp = StudentPractice.objects.get(pk=sp_id)
                if sp.workflow_state in (
                    StudentPracticeWorkflowState.ENDED,
                    StudentPracticeWorkflowState.COMPLETED,
                ):
                    request = self.context.get("request")
                    has_file = bool(data.get("pdf_file")) or (request and request.FILES.get("pdf_file"))
                    if not has_file:
                        raise serializers.ValidationError({"pdf_file": "PDF je povinný pro ukončené praxe."})
            except StudentPractice.DoesNotExist:
                pass
        return data

    def validate_expertise_rating(self, val):
        if not (1 <= val <= 5):
            raise serializers.ValidationError("Hodnocení musí být v rozmezí 1 až 5.")
        return val

    def validate_communication_rating(self, val):
        if not (1 <= val <= 5):
            raise serializers.ValidationError("Hodnocení musí být v rozmezí 1 až 5.")
        return val

    def validate_initiative_rating(self, val):
        if not (1 <= val <= 5):
            raise serializers.ValidationError("Hodnocení musí být v rozmezí 1 až 5.")
        return val
