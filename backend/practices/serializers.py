from datetime import date

from rest_framework import serializers

from api.helpers import FormattedDateField
from practices.models import Practice, ProgressStatus
from practices.utils import calculate_end_date
from student_practices.models import StudentPractice
from student_practices.serializers import StudentPracticeStatusSerializer
from subject.models import Subject
from subject.serializers import SubjectSerializer
from users.models import ApprovalStatus, EmployerProfile, User
from users.serializers import EmployerProfileSerializer


class OrganizationPracticeSerializer(serializers.ModelSerializer):
    """Serializer pro zobrazení praxí organizace"""

    contact_user_full_name = serializers.CharField(source="contact_user.full_name", read_only=True)
    created_at = FormattedDateField(read_only=True)

    # Statistiky studentů
    approved_applications = serializers.SerializerMethodField()
    pending_applications = serializers.SerializerMethodField()

    class Meta:
        model = Practice
        fields = [
            "practice_id",
            "title",
            "contact_user_full_name",
            "created_at",
            "available_positions",
            "approved_applications",
            "pending_applications",
            "approval_status",
        ]

    def get_approved_applications(self, obj):
        if hasattr(obj, "approved_count"):
            return obj.approved_count
        return obj.student_practices.filter(approval_status=ApprovalStatus.APPROVED).count()

    def get_pending_applications(self, obj):
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
    student_practice_status = serializers.SerializerMethodField(read_only=True)
    student_practice_documents = serializers.SerializerMethodField(read_only=True)
    start_date = FormattedDateField()
    end_date = FormattedDateField(required=False)

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

    def get_student_practice_documents(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        from users.models import StudentUser

        try:
            student = StudentUser.objects.get(user_id=request.user.id)
        except StudentUser.DoesNotExist:
            return []

        student_practice_documents = []
        approved_practices = StudentPractice.objects.filter(
            user=student,
            practice=obj,
            approval_status=ApprovalStatus.APPROVED,
        )
        for sp in approved_practices:
            if sp.contract_document_id:
                student_practice_documents.append({"id": sp.contract_document_id, "type": "contract"})
            if sp.content_document_id:
                student_practice_documents.append({"id": sp.content_document_id, "type": "content"})
            if sp.feedback_document_id:
                student_practice_documents.append({"id": sp.feedback_document_id, "type": "feedback"})

        return student_practice_documents

    def get_student_practice_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        try:
            student_practice = StudentPractice.objects.get(user_id=request.user.id, practice=obj)
            return StudentPracticeStatusSerializer(student_practice).data
        except (StudentPractice.DoesNotExist, StudentPractice.MultipleObjectsReturned):
            pass

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
            "contact_user",
            "contact_user_info",
            "student_practice_documents",
            "is_active",
            "image_base64",
            "coefficient",
            "student_practice_status",
        ]
        read_only_fields = ["practice_id", "is_active"]

    def validate(self, data):
        """
        Zkontroluje, zda end_date není před start_date, a že start_date >= dnešek.
        """
        start = data.get("start_date")
        end = data.get("end_date")

        if start and start < date.today():
            raise serializers.ValidationError("Datum zahájení nemůže být v minulosti.")

        if start and end and end < start:
            raise serializers.ValidationError("Datum ukončení nemůže být před datem zahájení.")

        return data

    def create(self, validated_data):
        validated_data.setdefault("is_active", True)
        validated_data.setdefault("progress_status", ProgressStatus.NOT_STARTED)
        validated_data.setdefault("approval_status", ApprovalStatus.PENDING)

        start_date = validated_data.get("start_date")
        coefficient = validated_data.get("coefficient")
        if start_date and coefficient is not None:
            validated_data["end_date"] = calculate_end_date(start_date, coefficient)

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
        ]
        read_only_fields = ["practice_id", "is_active"]

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
            raise serializers.ValidationError("Datum ukončení nemůže být před datem zahájení.")
        if start and start < date.today():
            raise serializers.ValidationError("Datum zahájení nemůže být v minulosti.")
        return data

    def create(self, validated_data):
        if "is_active" not in validated_data:
            validated_data["is_active"] = True
        if "progress_status" not in validated_data:
            validated_data["progress_status"] = ProgressStatus.NOT_STARTED
        if "approval_status" not in validated_data:
            validated_data["approval_status"] = ApprovalStatus.PENDING
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
        ]


class PracticeApprovalStatusSerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(
        choices=[(choice[1], choice[1]) for choice in ApprovalStatus.choices() if choice[0] != ApprovalStatus.PENDING],
        help_text="Status schválení praxe (pouze pro schválení nebo zamítnutí)",
    )


class EndDateRequestSerializer(serializers.Serializer):
    start_date = FormattedDateField(help_text="Start date")
    coefficient = serializers.FloatField(help_text="Coefficient to calculate practice duration")


class EndDateResponseSerializer(serializers.Serializer):
    end_date = FormattedDateField(help_text="Calculated end date")
