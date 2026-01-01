from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api.helpers import Base64ImageField
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubject,
    UserSubjectType,
    UserType,
)
from users.services import (
    get_or_create_stag_user,
    register_organization,
    validate_stag_ticket,
)

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    service_ticket = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # override parent’s password field to be optional/blank
        pw = self.fields["password"]
        pw.required = False
        pw.allow_blank = True
        pw.write_only = True
        email = self.fields["email"]
        email.required = False
        email.allow_blank = True
        email.write_only = True

    def validate(self, attrs):
        ticket = attrs.pop("service_ticket", None)

        if ticket:
            try:
                stag_data = validate_stag_ticket(ticket)
                user = get_or_create_stag_user(stag_data, ticket)
                if not user:
                    raise AuthenticationFailed("Could not create or retrieve STAG user.")

                # Update last login manually since we bypassed authenticate()
                update_last_login(None, user)

                refresh = self.get_token(user)
                refresh["type"] = UserType.STAG.value
                refresh["service_ticket"] = ticket
                return {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": user,
                }
            except Exception as e:
                raise AuthenticationFailed(str(e))

        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            return self._validate_with_credentials(email, password)

        raise AuthenticationFailed("Email and password are required")

    def _validate_with_credentials(self, email, password):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("No account found with this email address")

        if not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed("Invalid credentials or disabled account")

        # authenticate() updates last_login internally if used, but here we verify manually.
        update_last_login(None, user)

        refresh = self.get_token(user)
        if isinstance(user, OrganizationUser):
            # organization_role = user.organization_role
            refresh["type"] = UserType.ORGANIZATION.value
        else:
            refresh["type"] = "undefined"

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user,
        }


class OrganizationRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    ico = serializers.RegexField(regex=r"^\d{1,8}$", write_only=True, required=True)
    email = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=True)
    logo = serializers.ImageField(write_only=True, required=False)
    companyName = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    dic = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "phone",
            "password",
            "password2",
            "ico",
            "first_name",
            "last_name",
            "title_before",
            "title_after",
            "logo",
            "companyName",
            "address",
            "dic",
        )
        extra_kwargs = {
            "ico": {"required": True},
            "email": {"required": True},
            "phone": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        try:
            return register_organization(validated_data)
        except ValueError as e:
            raise serializers.ValidationError({"ARES": str(e)})


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Nová hesla se neshodují."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Nová hesla se neshodují."})
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to invalidate")


class AresJusticeSerializer(serializers.Serializer):
    ico = serializers.RegexField(regex=r"\d{8}")


class UserInfoSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    role = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    favorite_practices = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "firstName", "lastName", "department", "favorite_practices"]

    def get_role(self, obj):
        if obj.is_superuser or obj.email == "admin@admin.com":
            return "admin"
        return obj.role or ""

    def get_department(self, obj):
        if not hasattr(obj, "stag_role") or not obj.stag_role:
            return None

        stag_role_name = obj.stag_role.role if hasattr(obj.stag_role, "role") else str(obj.stag_role)
        if stag_role_name.lower() in ["vk", "vy"] and hasattr(obj, "department") and obj.department:
            return {
                "id": obj.department.department_id,
                "name": obj.department.department_name,
                "code": obj.department.department_code,
            }
        return None

    def get_favorite_practices(self, obj):
        if hasattr(obj, "favorite_practices"):
            return list(obj.favorite_practices.values_list("pk", flat=True))
        return []


class TokenResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserInfoSerializer()


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(read_only=True)
    user_type = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "title_before",
            "title_after",
            "first_name",
            "last_name",
            "user_type",
            "role",
        ]

    def validate_email(self, value):
        # Pokud se email nemění, přeskočit validaci
        if self.instance and self.instance.email == value:
            return value

        # Jinak zkontrolovat unikátnost (s vyloučením sebe sama pro jistotu, i když by to mělo pokrýt if výše)
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Uživatel s tímto emailem již existuje.")
        return value

    def get_user_type(self, obj):
        if isinstance(obj, StudentUser):
            return "student"
        elif isinstance(obj, ProfessorUser):
            return "professor"
        elif isinstance(obj, OrganizationUser):
            return "organization"
        else:
            return "unknown"

    def get_role(self, obj):
        return obj.role


class StudentProfileSerializer(UserProfileSerializer):
    cv_file = serializers.FileField(read_only=True)

    class Meta(UserProfileSerializer.Meta):
        model = StudentUser
        fields = UserProfileSerializer.Meta.fields + [
            "profile_picture",
            "resume",
            "additional_info",
            "street",
            "street_number",
            "zip_code",
            "city",
            "specialization",
            "skills",
            "cv_file",
        ]


class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = [
            "employer_id",
            "ico",
            "dic",
            "company_name",
            "address",
            "company_profile",
            "zip_code",
            "approval_status",
            "logo",
        ]
        read_only_fields = ["employer_id"]

    def validate_ico(self, value):
        # Check if ICO exists, but exclude self if updating
        qs = EmployerProfile.objects.filter(ico=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Společnost s tímto IČO již existuje.")
        return value

    def create(self, validated_data):
        validated_data.setdefault("approval_status", ApprovalStatus.PENDING.value)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class StudentUserProfileSerializer(UserProfileSerializer):
    profile_picture = Base64ImageField(required=False, allow_null=True)
    cv_file = serializers.FileField(required=False, allow_null=True)
    favorite_practices = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(UserProfileSerializer.Meta):
        model = StudentUser
        fields = UserProfileSerializer.Meta.fields + [
            "profile_picture",
            "resume",
            "additional_info",
            "street",
            "street_number",
            "zip_code",
            "city",
            "specialization",
            "field_of_study",
            "year_of_study",
            "os_cislo",
            "skills",
            "cv_file",
            "favorite_practices",
        ]

    def validate_skills(self, value):
        if isinstance(value, str):
            import json

            try:
                return json.loads(value)
            except ValueError:
                return []
        return value


class ProfessorUserProfileSerializer(UserProfileSerializer):
    class Meta(UserProfileSerializer.Meta):
        model = ProfessorUser
        fields = UserProfileSerializer.Meta.fields + [
            "ucit_idno",
        ]


class OrganizationUserProfileSerializer(UserProfileSerializer):
    employer_profile = serializers.SerializerMethodField()

    class Meta(UserProfileSerializer.Meta):
        model = OrganizationUser
        fields = UserProfileSerializer.Meta.fields + [
            "employer_profile",
        ]

    def get_employer_profile(self, obj):
        if hasattr(obj, "employer_profile") and obj.employer_profile:
            return {
                "id": obj.employer_profile.employer_id,
                "company_name": obj.employer_profile.company_name,
                "ico": obj.employer_profile.ico,
                "city": obj.employer_profile.city,
                "address": obj.employer_profile.address,
                "zip_code": obj.employer_profile.zip_code,
                "logo": (obj.employer_profile.logo.url if obj.employer_profile.logo else None),
            }
        return None


class AdminOrganizationSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = [
            "employer_id",
            "ico",
            "dic",
            "company_name",
            "address",
            "zip_code",
            "approval_status",
            "logo",
            "owner",
        ]

    def get_owner(self, obj):
        owner = OrganizationUser.objects.filter(employer_profile=obj, organization_role=OrganizationRole.OWNER).first()
        if owner:
            return {
                "id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
            }
        return None


class AllStudentsListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department = serializers.SerializerMethodField()

    class Meta:
        model = StudentUser
        fields = [
            "user_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "os_cislo",
            "department",
            "is_active",
            "date_joined",
        ]

    def get_department(self, obj):
        # Získáme katedru studenta přes jeho předměty
        user_subjects = UserSubject.objects.filter(user=obj, role=UserSubjectType.Student.value).select_related("subject__department")

        departments = set()
        for user_subject in user_subjects:
            if user_subject.subject.department:
                departments.add(user_subject.subject.department.department_name)

        return list(departments) if departments else None


class OrganizationUserListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)
    role = serializers.SerializerMethodField()
    employer_name = serializers.CharField(source="employer_profile.company_name", read_only=True, allow_null=True)

    class Meta:
        model = OrganizationUser
        fields = ["id", "name", "role", "employer_name"]

    def get_role(self, obj):
        if obj.organization_role is not None:
            # If it's an integer enum value
            if isinstance(obj.organization_role, int):
                try:
                    return OrganizationRole(obj.organization_role).name
                except Exception:
                    return str(obj.organization_role)
            # If it's an Enum object
            elif hasattr(obj.organization_role, "name"):
                return obj.organization_role.name
            # If it's a ForeignKey or object with role_name
            elif hasattr(obj.organization_role, "role_name") and obj.organization_role.role_name:
                return obj.organization_role.role_name
            elif hasattr(obj.organization_role, "role") and obj.organization_role.role:
                return obj.organization_role.role
            else:
                return str(obj.organization_role)
        return None
