from datetime import date

from rest_framework import serializers

from .models import Department, EmployerProfile, Practice, PracticeType, PracticeUser, Status, StudentPractice, Subject, User


class StatusSerializer(serializers.ModelSerializer):
    """
    Serializer pro model Status
    - status_id: primární klíč (read-only)
    - status_name: název statusu
    - is_active: boolean, zda je status aktivní
    """

    class Meta:
        model = Status
        fields = "__all__"
        read_only_fields = ["status_id"]

    def validate_status_name(self, value):
        if not value:
            raise serializers.ValidationError("Název statusu je povinný.")
        return value

    def create(self, validated_data):
        # Nastav výchozí hodnotu is_active, pokud není poskytnuta
        if "is_active" not in validated_data:
            validated_data["is_active"] = True
        return super().create(validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer pro model Department
    - department_id: primární klíč (read-only)
    - department_name: název oddělení
    - description: popis oddělení
    """

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["department_id"]

    def validate_department_name(self, value):
        if Department.objects.filter(department_name=value).exists():
            raise serializers.ValidationError("Oddělení s tímto názvem již existuje.")
        return value


class SubjectSerializer(serializers.ModelSerializer):
    """
    Serializer pro model Subject
    - subject_id: primární klíč (read-only)
    - subject_code: unikátní kód předmětu
    - subject_name: název předmětu
    - department: nested Department (read-only)
    - department_id: PK oddělení (write-only, volitelné)
    - hours_required: počet hodin požadovaných
    """

    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", write_only=True, required=False
    )

    class Meta:
        model = Subject
        fields = [
            "subject_id",
            "subject_code",
            "subject_name",
            "department",
            "department_id",
            "hours_required",
        ]
        read_only_fields = ["subject_id"]

    def validate_subject_code(self, value):
        if Subject.objects.filter(subject_code=value).exists():
            raise serializers.ValidationError("Předmět s tímto kódem již existuje.")
        return value

    def create(self, validated_data):
        """
        Pokud není uvedeno hours_required, nastaví výchozí hodnotu 0.
        """
        if "hours_required" not in validated_data:
            validated_data["hours_required"] = 0
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


# ------------------------------------------------------------
# 8. EmployerProfileSerializer
# ------------------------------------------------------------
class EmployerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pro model EmployerProfile
    - employer_id: primární klíč (read-only)
    - company_name: název společnosti
    - ico: identifikační číslo (IČO)
    - dic: DIČ (daňové identifikační číslo)
    - address: adresa společnosti
    - company_profile: popis společnosti
    - approval_status: nested Status (read-only)
    - approval_status_id: PK statusu (write-only, volitelné)
    """

    approval_status = StatusSerializer(read_only=True)
    approval_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="approval_status", write_only=True, required=False
    )

    class Meta:
        model = EmployerProfile
        fields = [
            "employer_id",
            "company_name",
            "ico",
            "dic",
            "address",
            "company_profile",
            "approval_status",
            "approval_status_id",
        ]
        read_only_fields = ["employer_id"]

    def validate_ico(self, value):
        if EmployerProfile.objects.filter(ico=value).exists():
            raise serializers.ValidationError("Společnost s tímto IČO již existuje.")
        return value

    def create(self, validated_data):
        """
        Nastaví výchozí approval_status na 'pending', pokud není zadán.
        """
        if "approval_status" not in validated_data:
            pending = Status.objects.filter(status_name__icontains="pending").first()
            if pending:
                validated_data["approval_status"] = pending
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


# ------------------------------------------------------------
# 11. PracticeTypeSerializer
# ------------------------------------------------------------
class PracticeTypeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model PracticeType
    - practice_type_id: primární klíč (read-only)
    - name: název typu praxe
    - description: popis typu praxe
    """

    class Meta:
        model = PracticeType
        fields = "__all__"
        read_only_fields = ["practice_type_id"]

    def validate_name(self, value):
        if PracticeType.objects.filter(name=value).exists():
            raise serializers.ValidationError("Tento typ praxe již existuje.")
        return value


# ------------------------------------------------------------
# 12. PracticeSerializer
# ------------------------------------------------------------
class PracticeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model Practice
    - practice_id: primární klíč (read-only)
    - employer: nested EmployerProfile (read-only)
    - employer_id: PK zaměstnavatele (write-only)
    - subject: nested Subject (read-only)
    - subject_id: PK předmětu (write-only)
    - title: název praxe
    - description: popis praxe
    - responsibilities: povinnosti
    - available_positions: počet volných míst
    - start_date: datum zahájení
    - end_date: datum ukončení
    - status: nested Status (read-only)
    - status_id: PK statusu (write-only)
    - approval_status: nested Status (read-only)
    - approval_status_id: PK statusu schválení (write-only)
    - contact_user: PK uživatele, který je kontaktem (write-only)
    - contact_user_info: informace o kontaktu (user_id, username) (read-only)
    - is_active: boolean, zda je praxe aktivní (read-only)
    - image_base64: base64 reprezentace obrázku (string)
    - practice_type: nested PracticeType (read-only)
    - practice_type_id: PK typu praxe (write-only)
    """

    employer = EmployerProfileSerializer(read_only=True)
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployerProfile.objects.all(), source="employer", write_only=True, required=True
    )

    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), source="subject", write_only=True, required=True)

    status = StatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(queryset=Status.objects.all(), source="status", write_only=True, required=False)

    approval_status = StatusSerializer(read_only=True)
    approval_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="approval_status", write_only=True, required=False
    )

    contact_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    contact_user_info = serializers.SerializerMethodField(read_only=True)

    practice_type = PracticeTypeSerializer(read_only=True)
    practice_type_id = serializers.PrimaryKeyRelatedField(
        queryset=PracticeType.objects.all(), source="practice_type", write_only=True, required=False
    )

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
            "status",
            "status_id",
            "approval_status",
            "approval_status_id",
            "contact_user",
            "contact_user_info",
            "is_active",
            "image_base64",
            "practice_type",
            "practice_type_id",
        ]
        read_only_fields = ["practice_id", "is_active"]

    def get_contact_user_info(self, obj):
        if obj.contact_user:
            return {
                "user_id": obj.contact_user.user_id,
                "username": obj.contact_user.username,
            }
        return None

    def validate(self, data):
        """
        Zkontroluje, zda end_date není před start_date, a že start_date >= dnešek.
        """
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("Datum ukončení nemůže být před datem zahájení.")
        if start and start < date.today():
            raise serializers.ValidationError("Datum zahájení nemůže být v minulosti.")
        return data

    def create(self, validated_data):
        """
        Nastaví výchozí hodnotu is_active=True a případně status a approval_status.
        """
        if "is_active" not in validated_data:
            validated_data["is_active"] = True
        if "status" not in validated_data:
            default_status = Status.objects.filter(status_name__icontains="open").first()
            if default_status:
                validated_data["status"] = default_status
        if "approval_status" not in validated_data:
            pending_status = Status.objects.filter(status_name__icontains="pending").first()
            if pending_status:
                validated_data["approval_status"] = pending_status
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


# ------------------------------------------------------------
# 13. PracticeUserSerializer
# ------------------------------------------------------------
class PracticeUserSerializer(serializers.ModelSerializer):
    """
    Serializer pro model PracticeUser
    - id: primární klíč (read-only)
    - practice: nested Practice (read-only)
    - practice_id: PK praxe (write-only)
    - user: PK uživatele (write-only)
    - user_info: informace o uživateli (user_id, username)
    """

    practice = PracticeSerializer(read_only=True)
    practice_id = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), source="practice", write_only=True, required=True)

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=True)
    user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PracticeUser
        fields = [
            "id",
            "practice",
            "practice_id",
            "user",
            "user_info",
        ]
        read_only_fields = ["id", "practice", "user_info"]

    def get_user_info(self, obj):
        if obj.user:
            return {
                "user_id": obj.user.user_id,
                "username": obj.user.username,
            }
        return None

    def validate(self, data):
        """
        Zkontroluje, zda uživatel již není přiřazen k této praxi.
        """
        practice = data.get("practice")
        user = data.get("user")
        if PracticeUser.objects.filter(practice=practice, user=user).exists():
            raise serializers.ValidationError("Uživatel je již přiřazen k této praxi.")
        return data


# ------------------------------------------------------------
# 14. StudentPracticeSerializer
# ------------------------------------------------------------
class StudentPracticeSerializer(serializers.ModelSerializer):
    """
    Serializer pro model StudentPractice
    - student_practice_id: primární klíč (read-only)
    - practice: PK praxe (write-only)
    - title: název praxe (read-only)
    - logo: base64 obrázek praxe (read-only)
    - application_date: datum podání (read-only)
    - approval_status: nested Status (read-only)
    - approval_status_id: PK statusu schválení (write-only)
    - progress_status: nested Status (read-only)
    - progress_status_id: PK statusu průběhu (write-only)
    - hours_completed: počet dokončených hodin
    - cancellation_reason: důvod zrušení
    - cancelled_by_user: PK uživatele, kdo zrušil (write-only, volitelné)
    - cancelled_by_user_info: informace o uživateli, který zrušil (read-only)
    """

    practice = serializers.PrimaryKeyRelatedField(queryset=Practice.objects.all(), write_only=True, required=True)
    title = serializers.CharField(source="practice.title", read_only=True)
    logo = serializers.CharField(source="practice.image_base64", read_only=True)

    approval_status = StatusSerializer(read_only=True)
    approval_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="approval_status", write_only=True, required=False
    )

    progress_status = StatusSerializer(read_only=True)
    progress_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="progress_status", write_only=True, required=False
    )

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
            "approval_status_id",
            "progress_status",
            "progress_status_id",
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
            "approval_status",
            "progress_status",
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
            pending_status = Status.objects.filter(status_name__icontains="pending").first()
            if pending_status:
                validated_data["approval_status"] = pending_status
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
