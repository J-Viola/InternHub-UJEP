from api.helpers import FormattedDateField
from api.models import Practice, StudentPractice, UploadedDocument
from rest_framework import serializers


class EmployerInvitationApprovalSerializer(serializers.Serializer):
    invitation_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["accept", "reject"])


class StudentPracticeSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = StudentPractice
        fields = [
            "student_practice_id",
            "user",
            "user_info",
            "application_date",
            "approval_status",
            "progress_status",
            "hours_completed",
            "cancellation_reason",
            "year",
        ]

    def get_user_info(self, obj):
        if obj.user:
            return {"user_id": obj.user.user_id, "full_name": obj.user.full_name, "email": obj.user.email}
        return None


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
                "os_cislo": obj.user.os_cislo if hasattr(obj.user, "os_cislo") else None,
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
    practice_type = serializers.SerializerMethodField()
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
        from api.serializers import EmployerProfileSerializer

        return EmployerProfileSerializer(obj.practice.employer).data

    def get_subject(self, obj):
        from api.serializers import SubjectSerializer

        return SubjectSerializer(obj.practice.subject).data

    def get_student_practice_documents(self, obj):
        student_practice_documents = []
        student_practice_documents.append({"id": obj.contract_document.document_id, "type": "contract"})
        student_practice_documents.append({"id": obj.content_document.document_id, "type": "content"})
        student_practice_documents.append({"id": obj.feedback_document.document_id, "type": "feedback"})
        return student_practice_documents
