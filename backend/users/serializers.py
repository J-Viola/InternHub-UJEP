from api.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubject,
    UserSubjectType,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import UserType
from users.services import (
    fetch_ares_data,
    get_or_create_stag_user,
    register_organization,
    validate_stag_ticket,
)

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    service_ticket = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password optional because we might login via Ticket
        self.fields["password"].required = False
        self.fields["email"].required = False

    @classmethod
    def get_token(cls, user):
        """
        Add custom claims to the token payload.
        This runs when the token is generated.
        """
        token = super().get_token(user)

        # Add custom claims
        token["email"] = user.email

        # Determine user type and role for the token payload
        if isinstance(user, OrganizationUser):
            token["user_type"] = UserType.ORGANIZATION.value
            # token["role"] = user.organization_role # If needed in token
        elif isinstance(user, StudentUser) or isinstance(user, ProfessorUser):
            token["user_type"] = UserType.STAG.value
        else:
            token["user_type"] = "admin" if user.is_superuser else "unknown"

        return token

    def validate(self, attrs):
        ticket = attrs.get("service_ticket")
        email = attrs.get("email")
        password = attrs.get("password")

        user = None

        # 1. Authentication Logic
        if ticket:
            # STAG Auth
            try:
                stag_data = validate_stag_ticket(ticket)
                user = get_or_create_stag_user(stag_data, ticket)
                if not user:
                    raise AuthenticationFailed(
                        "Could not create or retrieve STAG user."
                    )
            except Exception as e:
                raise AuthenticationFailed(str(e))

        elif email and password:
            # Standard Password Auth
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise AuthenticationFailed("No account found with this email address")

            if not user.check_password(password):
                raise AuthenticationFailed("Invalid credentials")

            if not user.is_active:
                raise AuthenticationFailed("Account is disabled")
        else:
            raise AuthenticationFailed("Email/Password or Service Ticket required.")

        # 2. Generate Tokens using parent logic logic manually
        # (Because parent.validate() expects 'email'/'password' in attrs specifically for authenticate())

        # Update last login manually since we bypassed authenticate()
        update_last_login(None, user)

        # Generate tokens
        refresh = self.get_token(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        # 3. Add User Info to Response (kept for frontend convenience)
        # Note: Ideally, user info should be fetched via /api/users/profile/,
        # but keeping it here to match previous structure.
        self.user = user  # Save for the View to use if needed

        # We return user object in the dict so the View can serialize it
        data["user"] = user

        return data


class OrganizationRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
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
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        try:
            return register_organization(validated_data)
        except ValueError as e:
            raise serializers.ValidationError({"ARES": str(e)})


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to invalidate")


class AresJusticeSerializer(serializers.Serializer):
    ico = serializers.RegexField(regex=r"\d{8}")


class UserInfoSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    role = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "firstName", "lastName", "department"]

    def get_role(self, obj):
        if obj.is_superuser or obj.email == "admin@admin.com":
            return "admin"
        return obj.role or ""

    def get_department(self, obj):
        if not hasattr(obj, "stag_role") or not obj.stag_role:
            return None

        stag_role_name = (
            obj.stag_role.role if hasattr(obj.stag_role, "role") else str(obj.stag_role)
        )
        if (
            stag_role_name.lower() in ["vk", "vy"]
            and hasattr(obj, "department")
            and obj.department
        ):
            return {
                "id": obj.department.department_id,
                "name": obj.department.department_name,
                "code": obj.department.department_code,
            }
        return None


class TokenResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserInfoSerializer()


class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = StudentUser
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "profile_picture",
            "resume",
            "additional_info",
            "street",
            "street_number",
            "zip_code",
            "city",
            "specialization",
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


class UserProfileSerializer(serializers.ModelSerializer):
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


class StudentUserProfileSerializer(UserProfileSerializer):
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
        ]


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
                "logo": (
                    obj.employer_profile.logo.url if obj.employer_profile.logo else None
                ),
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
        owner = OrganizationUser.objects.filter(
            employer_profile=obj, organization_role=OrganizationRole.OWNER
        ).first()
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
        user_subjects = UserSubject.objects.filter(
            user=obj, role=UserSubjectType.Student.value
        ).select_related("subject__department")

        departments = set()
        for user_subject in user_subjects:
            if user_subject.subject.department:
                departments.add(user_subject.subject.department.department_name)

        return list(departments) if departments else None


class OrganizationUserListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)
    role = serializers.SerializerMethodField()
    employer_name = serializers.CharField(
        source="employer_profile.company_name", read_only=True, allow_null=True
    )

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
            elif (
                hasattr(obj.organization_role, "role_name")
                and obj.organization_role.role_name
            ):
                return obj.organization_role.role_name
            elif hasattr(obj.organization_role, "role") and obj.organization_role.role:
                return obj.organization_role.role
            else:
                return str(obj.organization_role)
        return None
