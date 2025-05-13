import requests
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from django.http import HttpResponse, JsonResponse

User = get_user_model()

class ServiceTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    1) Pops `service_token` from the incoming credentials
    2) Calls the 3rd‑party to validate and fetch email
    3) Looks up (or creates) a local User by that email
    4) Issues a JWT pair for *that* user, embedding service_token
    """
    token = serializers.CharField(write_only=True)


    def validate(self, attrs):
        ticket = attrs.pop("ticket", None)
        if not ticket or ticket == "anonymous":
            return JsonResponse({"error": "Authentication failed"}, status=401)

        try:

            # Construct the URL for getStagUserListForLoginTicket
            stag_api_url = f"{settings.STAG_WS_URL}/services/rest2/help/getStagUserListForLoginTicketV2"

            # Make the request with the ticket
            response = requests.get(
                stag_api_url,
                params={"ticket": ticket, "longTicket": "1"},
                timeout=(3.05, 27),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 200:
                # Process the response and store it
                stag_user_details = response.json()
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email.split("@")[0]}
        )
        refresh = self.get_token(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # 2) Call the 3rd‑party
        try:
            resp = requests.post(
                self.service_validation_url,
                json={"token": service_token},
                timeout=5,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise AuthenticationFailed(f"Service validation error: {e}")

        data = resp.json()
        if not data.get("valid"):
            raise AuthenticationFailed("Invalid service token")

        email = data.get("email")
        if not email:
            raise AuthenticationFailed("No email returned from service")

        # 3) Get or create the Django User
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email.split("@")[0]}
        )
        self.user = user  # important for TokenObtainPairSerializer

        # 4) Now generate the standard tokens for `self.user`
        refresh = self.get_token(self.user)
        refresh["service_token"] = service_token  # inject custom claim

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


