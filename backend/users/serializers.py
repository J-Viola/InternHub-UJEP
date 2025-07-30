import requests
from api.models import (
    ApprovalStatus,
    Department,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StudentUser,
    Subject,
    UserSubject,
    UserSubjectType,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.dtos.dtos import EkonomickySubjektDTO
from users.models import StagRoleEnum, UserType

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
            return self._validate_with_stag(ticket)

        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            return self._validate_with_credentials(email, password)

        raise AuthenticationFailed("Email and password are required")

    def _validate_with_stag(self, ticket):
        url = f"{settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"
        resp = requests.get(
            url,
            params={"ticket": ticket, "longTicket": "1"},
            timeout=(3.05, 27),
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            raise AuthenticationFailed("Failed to authenticate with STAG")

        details = resp.json()
        email = details.get("email")
        jmeno = details.pop("jmeno")
        prijmeni = details.pop("prijmeni")
        # https://ws.ujep.cz/ws/services/rest2/student/getStudentInfo?osCislo=F22248&outputFormat=JSON&semestr=%20&rok=2024
        stagUserInfos = details.get("stagUserInfo")
        if not stagUserInfos or len(stagUserInfos) == 0:
            raise AuthenticationFailed("No user information returned by STAG")
        # TODO pro každý info.. se musí asi udělat účet... píče
        stagUserInfo = stagUserInfos[0]
        role = stagUserInfo["role"]
        roleName = stagUserInfo["roleNazev"]
        if not email:
            raise AuthenticationFailed("Email not returned by STAG")
        osCislo = stagUserInfo.get("osCislo")
        ucitIdno = stagUserInfo.get("ucitIdno")

        stagRole, _ = StagRole.objects.get_or_create(role=role, defaults={"role": role, "role_name": roleName})
        if osCislo:
            user, _ = StudentUser.objects.get_or_create(
                email=email,
                defaults={
                    "email": email,
                    "stag_role": stagRole,
                    "first_name": jmeno,
                    "last_name": prijmeni,
                    "os_cislo": osCislo,
                    "is_active": True,
                },
            )
            sync_stag_subjects_for_student(ticket, osCislo, user)
        if ucitIdno:
            try:
                user = ProfessorUser.objects.get(email=email)
            except ProfessorUser.DoesNotExist:
                katedra = stagUserInfo.get("katedra")
                try:
                    department = Department.objects.get(department_code=katedra)
                except Department.DoesNotExist:
                    raise AuthenticationFailed(f"Katedra {katedra} nebyla nalezena v databázi. Kontaktujte správce systému")
                department_role = DepartmentRole.HEAD if stagRole.role == StagRoleEnum.VK else DepartmentRole.TEACHER
                user, _ = ProfessorUser.objects.get_or_create(
                    email=email,
                    defaults={
                        "email": email,
                        "stag_role": stagRole,
                        "first_name": jmeno,
                        "last_name": prijmeni,
                        "ucit_idno": ucitIdno,
                        "is_active": True,
                        "department": department,
                        "department_role": department_role,
                    },
                )
            sync_stag_roles_for_teacher(ticket, ucitIdno, user)

        refresh = self.get_token(user)
        refresh["type"] = UserType.STAG.value
        refresh["service_ticket"] = ticket

        return {"refresh": str(refresh), "access": str(refresh.access_token), "user": user}

    def _validate_with_credentials(self, email, password):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("No account found with this email address")

        if not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed("Invalid credentials or disabled account")

        refresh = self.get_token(user)
        if isinstance(user, OrganizationUser):
            # organization_role = user.organization_role
            refresh["type"] = UserType.ORGANIZATION.value
        else:
            refresh["type"] = "undefined"

        return {"refresh": str(refresh), "access": str(refresh.access_token), "user": user}


# class CustomTokenRefreshSerializer(TokenRefreshSerializer):
#     def validate(self, attrs):
#         # decode old refresh
#         refresh = RefreshToken(attrs["refresh"])
#         # re-fetch user
#         # lookup user by configured claim
#         user_id = refresh[api_settings.USER_ID_CLAIM]
#         try:
#             user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
#         except User.DoesNotExist:
#             raise AuthenticationFailed("User not found", code="user_not_found")
#         self.user = user
#
#         # optionally rotate/blacklist old refresh
#         if api_settings.ROTATE_REFRESH_TOKENS:
#             refresh.blacklist()
#             refresh = RefreshToken.for_user(user)
#
#         # build new access
#         access = refresh.access_token
#
#         # inject fresh claims
#         access["type"] = user
#         if isinstance(user.user_type, OrganizationUser):
#             access["role"] = user.organization_role.role
#         elif user.user_type == UserType.STAG.value:
#             access["role"] = user.stag_role.role
#         elif user.is_superuser:
#             access["role"] = UserType.ADMIN.value
#
#         data = {"access": str(access)}
#         if self.rotate_refresh_tokens:
#             data["refresh"] = str(refresh)
#         return data


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

        ico = validated_data.pop("ico")
        company_name = validated_data.pop("companyName", "")
        address = validated_data.pop("address", "")
        dic = validated_data.pop("dic", "")

        ico = str(ico).zfill(8)
        cache_key = f"ares_{ico}"
        ares_data = cache.get(cache_key)

        if not ares_data:
            response = requests.get("https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/" + ico)
            if response.status_code == 200:
                response_data = response.json()
                if "kod" in response_data and response_data["kod"] is not None:
                    raise serializers.ValidationError({"ARES": "ARES returned an error code."})
                ares_data = EkonomickySubjektDTO.model_validate(response_data)
                cache.set(cache_key, ares_data, timeout=3600)
            else:
                raise serializers.ValidationError({"ARES": "Failed to fetch data from ARES"})

        with transaction.atomic():
            user = OrganizationUser.objects.create(
                email=validated_data["email"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                title_before=validated_data.get("title_before", ""),
                title_after=validated_data.get("title_after", ""),
                phone=validated_data.get("phone", ""),
                organization_role=OrganizationRole.OWNER,
                is_active=True,  # TODO: Remove this
            )

            # Use frontend data if provided, otherwise fall back to ARES data
            if hasattr(ares_data, "sidlo"):
                sidlo = ares_data.sidlo
            else:
                sidlo = ares_data.get("sidlo", {})

            employer_profile = EmployerProfile.objects.create(
                employer_id=user.id,
                ico=ico,
                dic=dic if dic else (ares_data.dic if hasattr(ares_data, "dic") else ares_data.get("dic", "")),
                company_name=(
                    company_name
                    if company_name
                    else (ares_data.obchodniJmeno if hasattr(ares_data, "obchodniJmeno") else ares_data.get("companyName", ""))
                ),
                address=(
                    address
                    if address
                    else (
                        sidlo.textovaAdresa
                        if hasattr(sidlo, "textovaAdresa")
                        else (sidlo.get("address", "") if isinstance(sidlo, dict) else "")
                    )
                ),
                zip_code=sidlo.psc if hasattr(sidlo, "psc") else (sidlo.get("psc", "") if isinstance(sidlo, dict) else ""),
                approval_status=ApprovalStatus.PENDING,
                logo=validated_data["logo"] if "logo" in validated_data else None,
            )

            # Update the user to link to the employer profile
            user.employer_profile = employer_profile
            user.set_password(validated_data["password"])
            user.save()

            return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to invalidate")


class AresJusticeSerializer(serializers.Serializer):
    ico = serializers.RegexField(regex=r"\d{8}")


class UserInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField(allow_null=True)
    firstName = serializers.CharField()
    lastName = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserInfoSerializer()


class PredmetStudentaSerializer(serializers.Serializer):
    katedra = serializers.CharField()
    kredity = serializers.IntegerField()
    nazev = serializers.CharField()
    rok = serializers.CharField()
    statut = serializers.CharField()
    uznano = serializers.CharField()
    zkratka = serializers.CharField()


class PredmetUciteleSerializer(serializers.Serializer):
    cvicici = serializers.SerializerMethodField()
    cviciciPodil = serializers.IntegerField()
    examinator = serializers.SerializerMethodField()
    garant = serializers.SerializerMethodField()
    garantPodil = serializers.IntegerField(allow_null=True)
    katedra = serializers.CharField()
    nazev = serializers.CharField()
    prednasejici = serializers.SerializerMethodField()
    rok = serializers.CharField()
    seminarici = serializers.SerializerMethodField()
    seminariciPodil = serializers.IntegerField()
    zkratka = serializers.CharField()

    def get_cvicici(self, obj):
        value = obj.get("cvicici", "")
        if value.upper() == "ANO":
            return True
        elif value.upper() == "NE":
            return False
        return None

    def get_examinator(self, obj):
        value = obj.get("examinator", "")
        if value.upper() == "ANO":
            return True
        elif value.upper() == "NE":
            return False
        return None

    def get_garant(self, obj):
        value = obj.get("garant", "")
        if value.upper() == "ANO":
            return True
        elif value.upper() == "NE":
            return False
        return None

    def get_prednasejici(self, obj):
        value = obj.get("prednasejici", "")
        if value.upper() == "ANO":
            return True
        elif value.upper() == "NE":
            return False
        return None

    def get_seminarici(self, obj):
        value = obj.get("seminarici", "")
        if value.upper() == "ANO":
            return True
        elif value.upper() == "NE":
            return False
        return None


def sync_stag_subjects_for_student(stag_ticket: str, osCislo: str, user: StudentUser):
    """
    Synchronizes STAG roles with the database for student.
    """
    url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByStudent"
    params = {
        "osCislo": osCislo,
        "outputFormat": "JSON",
        "semestr": "%",
        "rok": "%",
    }

    cookies = {
        "WSCOOKIE": stag_ticket,
    }
    response = requests.get(url, cookies=cookies, params=params, timeout=(3.05, 27), headers={"Accept": "application/json"})

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetStudenta", [])
        serializer = PredmetStudentaSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)
        subject_data = serializer.validated_data
        for subj in subject_data:
            subjInDb = None
            try:
                subjInDb = Subject.objects.get(subject_code=subj["zkratka"])
            except Subject.DoesNotExist:
                pass
            if subjInDb is not None:
                UserSubject.objects.get_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={
                        "subject": subjInDb,
                        "user": user,
                        "role": UserSubjectType.Student,
                    },
                )
    else:
        raise Exception("Failed to fetch STAG roles")


def sync_stag_roles_for_teacher(stag_ticket: str, ucitIdno: str, user: ProfessorUser):
    """
    Synchronizes STAG roles with the database.
    """
    url = f"{settings.STAG_WS_URL}/services/rest2/predmety/getPredmetyByUcitel"
    params = {
        "ucitIdno": ucitIdno,
        "outputFormat": "JSON",
        "semestr": "%",
        "rok": "%",
    }

    cookies = {
        "WSCOOKIE": stag_ticket,
    }
    response = requests.get(url, cookies=cookies, params=params, timeout=(3.05, 27), headers={"Accept": "application/json"})

    if response.status_code == 200:
        response_json = response.json()
        items = response_json.get("predmetUcitele", [])
        serializer = PredmetUciteleSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)
        subject_data = serializer.validated_data
        for subj in subject_data:
            subjInDb = None
            try:
                subjInDb = Subject.objects.get(subject_code=subj["zkratka"])
            except Subject.DoesNotExist:
                pass
            if subjInDb is not None:
                UserSubject.objects.get_or_create(
                    subject=subjInDb,
                    user=user,
                    defaults={"subject": subjInDb, "user": user, "role": UserSubjectType.Professor},
                )
    else:
        raise Exception("Failed to fetch STAG roles")


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
            "zip_code",
            "approval_status",
            "logo",
        ]
        read_only_fields = ["employer_id", "approval_status"]


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
                "logo": obj.employer_profile.logo.url if obj.employer_profile.logo else None,
            }
        return None


class AdminOrganizationSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = ["employer_id", "ico", "dic", "company_name", "address", "zip_code", "approval_status", "logo", "owner"]

    def get_owner(self, obj):
        owner = OrganizationUser.objects.filter(employer_profile=obj, organization_role=OrganizationRole.OWNER).first()
        if owner:
            return {
                "id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
            }
        return None
