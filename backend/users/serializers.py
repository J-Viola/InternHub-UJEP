import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import UserType

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    service_ticket = serializers.CharField(write_only=True, required=False)
    email = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

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

        if not email:
            raise AuthenticationFailed("Email not returned by STAG")

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email.split("@")[0]},
            is_active=True,
        )

        refresh = self.get_token(user)
        refresh["type"] = UserType.STUDENT.value
        refresh["service_ticket"] = ticket

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    def _validate_with_credentials(self, email, password):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("No account found with this email address")

        if not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed("Invalid credentials or disabled account")

        refresh = self.get_token(user)
        refresh["type"] = UserType.ORGANIZATION.value

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class RegisterSerializer(serializers.ModelSerializer):
    ico = serializers.CharField(required=True, write_only=True)
    logo = serializers.ImageField(required=True, write_only=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
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
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
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
