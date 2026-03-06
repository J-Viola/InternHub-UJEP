from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Brute-force protection on the JWT login endpoint."""

    scope = "login"


class PasswordResetThrottle(AnonRateThrottle):
    """Prevents automated password-reset email flooding."""

    scope = "password_reset"
