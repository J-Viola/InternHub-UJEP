from rest_framework import status
from rest_framework.exceptions import APIException


class StagUnreachableError(APIException):
    """Raised when STAG server is unreachable or returns a connection error."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "STAG server is unavailable"
    default_code = "STAG_UNREACHABLE"
