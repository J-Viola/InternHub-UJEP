from datetime import date

from rest_framework import serializers

from api.helpers import FormattedDateField
from api.models import ApprovalStatus, EmployerInvitation, Practice, StudentPractice, UploadedDocument, User


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
    student_ids = serializers.ListField(child=serializers.IntegerField())


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
            "hours_completed",
            "cancellation_reason",
            "year",
            "start_date",
            "end_date",
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
    - cancelled_by_user: PK uživatele, kdo zrušil (write-only, volitelné)
    - cancelled_by_user_info: informace o uživateli, který zrušil (read-only)
    """

    practice = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), write_only=True, required=True)
    title = serializers.CharField(source="practice.title", read_only=True)
    logo = serializers.CharField(source="practice.image_base64", read_only=True)

    cancelled_by_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    cancelled_by_user_info = serializers.SerializerMethodField(read_only=True)

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
            "hours_completed",
            "cancellation_reason",
            "cancelled_by_user",
            "cancelled_by_user_info",
        ]
        read_only_fields = [
            "student_practice_id",
            "title",
            "logo",
            "application_date",
            "cancelled_by_user_info",
        ]

    def get_cancelled_by_user_info(self, obj):
        if obj.cancelled_by_user:
            return {
                "user_id": obj.cancelled_by_user.user_id,
                "username": obj.cancelled_by_user.username,
            }
        return None

    def validate(self, data):
        """
        Zkontroluje, zda student již není přihlášen na tuto praxi, a že hours_completed >= 0.
        """
        practice = data.get("practice")
        user = self.context["request"].user if "request" in self.context else None
        if user and StudentPractice.objects.filter(practice=practice, user=user).exists():
            raise serializers.ValidationError("Již jste přihlášen(a) na tuto praxi.")
        hours = data.get("hours_completed", 0)
        if hours < 0:
            raise serializers.ValidationError("Počet dokončených hodin nesmí být záporný.")
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
    department_name = serializers.CharField(source="practice.subject.department.department_name", read_only=True)
    application_date = FormattedDateField(read_only=True)
    student_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_id = serializers.IntegerField(source="user.user_id", read_only=True)
    # pro admin list view
    employer_id = serializers.IntegerField(source="practice.employer.employer_id", read_only=True)
    employer_name = serializers.CharField(source="practice.employer.company_name", read_only=True)

    class Meta:
        model = StudentPractice
        fields = [
            "practice_id",
            "student_practice_id",
            "department_name",
            "student_full_name",
            "user_id",
            "practice_title",
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
            "employer_id",
            "employer_name",
        ]
        read_only_fields = [
            "student_practice_id",
            "practice_title",
            "application_date",
        ]


class StudentPracticeStatusSerializer(serializers.ModelSerializer):
    application_date = FormattedDateField(read_only=True, allow_null=True)
    student_info = serializers.SerializerMethodField()

    class Meta:
        model = StudentPractice
        fields = [
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
            "student_info",
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
            "contact_user_info",
            "is_active",
            "image_base64",
            "student_practice_status",
            "student_practice_documents",
        ]

    def get_contact_user_info(self, obj):
        if obj.practice.contact_user:
            return {
                "user_id": obj.practice.contact_user.user_id,
                "username": obj.practice.contact_user.username,
            }
        return None

    def get_student_practice_status(self, obj):
        return StudentPracticeStatusSerializer(obj).data

    def get_employer(self, obj):
        from users.serializers import EmployerProfileSerializer

        return EmployerProfileSerializer(obj.practice.employer).data

    def get_subject(self, obj):
        from subject.serializers import SubjectSerializer

        return SubjectSerializer(obj.practice.subject).data

    def get_student_practice_documents(self, obj):
        student_practice_documents = []
        student_practice_documents.append({"id": obj.contract_document.document_id, "type": "contract"})
        student_practice_documents.append({"id": obj.content_document.document_id, "type": "content"})
        student_practice_documents.append({"id": obj.feedback_document.document_id, "type": "feedback"})
        return student_practice_documents
