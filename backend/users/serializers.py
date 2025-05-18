import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.http import HttpResponse, JsonResponse
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    service_ticket = serializers.CharField(write_only=True, required=False)
    email = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # make all three fields optional at parse time
        for fld in ("service_ticket", "email", "password"):
            self.fields[fld].required = False

    def validate(self, attrs):
        ticket = attrs.pop("service_ticket", None)
        if ticket:
            # STAG validation flow
            url = f"{
                settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"
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
            if not email:
                raise AuthenticationFailed("Email not returned by STAG")

            user, _ = User.objects.get_or_create(
                email=email, defaults={"username": email.split("@")[0]}
            )
            self.user = user
            refresh = self.get_token(user)
            refresh["service_ticket"] = ticket

            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise AuthenticationFailed("No account found with this email address")

            if not user.check_password(password):
                raise AuthenticationFailed("Invalid password")

            if not user.is_active:
                raise AuthenticationFailed("User account is disabled")

            refresh = self.get_token(user)

            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

        raise AuthenticationFailed("Email and password are required")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "password", "password2", "first_name", "last_name")
        extra_kwargs = {
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
        user = User.objects.create(
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=True,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to invalidate")
