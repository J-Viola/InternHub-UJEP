import requests
from api.models import (
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StagUser,
    Status,
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
from users.models import UserType

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

        stagUserInfos = details.get("stagUserInfo")
        if not stagUserInfos or len(stagUserInfos) == 0:
            raise AuthenticationFailed("No user information returned by STAG")
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
            user, _ = ProfessorUser.objects.get_or_create(
                email=email,
                defaults={
                    "email": email,
                    "stag_role": stagRole,
                    "first_name": jmeno,
                    "last_name": prijmeni,
                    "ucit_idno": ucitIdno,
                    "is_active": True,
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

    class Meta:
        model = User
        fields = ("email", "phone", "password", "password2", "ico", "logo")
        extra_kwargs = {
            "ico": {"required": True},
            "email": {"required": True},
            "phone": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        try:
            unregistered_role = OrganizationRole.objects.get(role="unregistered")
        except OrganizationRole.DoesNotExist:
            raise serializers.ValidationError({"organization_role": "Role 'unregistered' does not exist."})
        ico = validated_data.pop("ico")
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
                email=validated_data["email"], organization_role=unregistered_role, is_active=True  # TODO: Remove this
            )
            # TODO: Must be set in DB (migration maybe?+)
            status = Status.objects.get(status_name="Pending")
            EmployerProfile.objects.create(
                employer_id=user.id,
                ico=ares_data.icoId,
                dic=ares_data.dic,
                company_name=ares_data.obchodniJmeno,
                address=ares_data.sidlo.textAdresy,
                zip_code=ares_data.sidlo.psc,
                approval_status=status,
                # TODO: LOGO
                logo=validated_data["logo"] if "logo" in validated_data else None,
            )
            user.set_password(validated_data["password"])
            user.save()
            # TODO: Finish this with activation of the account by VEDENÍ KATEDRY approving and sending activation email?
            return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to invalidate")


class AresJusticeSerializer(serializers.Serializer):
    ico = serializers.RegexField(regex=r"\d{8}")


class UserInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField()
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


def sync_stag_subjects_for_student(stag_ticket: str, osCislo: str, user: StagUser):
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


def sync_stag_roles_for_teacher(stag_ticket: str, ucitIdno: str, user: StagUser):
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
                    defaults={"subject": subjInDb, "user": user, "role": UserSubjectType.Teacher},
                )
    else:
        raise Exception("Failed to fetch STAG roles")
