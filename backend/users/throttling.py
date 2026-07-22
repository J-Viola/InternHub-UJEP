from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Brute-force protection on the JWT login endpoint."""

    scope = "login"


class StagTicketThrottle(AnonRateThrottle):
    """Limits STAG ticket validation requests to prevent spamming STAG."""

    scope = "stag_ticket"


class PasswordResetThrottle(AnonRateThrottle):
    """Prevents automated password-reset email flooding."""

    scope = "password_reset"


class AresThrottle(AnonRateThrottle):
    scope = "ares"
