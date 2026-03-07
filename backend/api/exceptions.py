from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats responses into standard error codes.
    Returns: { "error_code": "CODE", "details": ... }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # 1. Handle native Python ValueError
    if response is None:
        if isinstance(exc, ValueError):
            # We assume ValueErrors raised in services use our new error codes
            return Response(
                {"error_code": str(exc), "details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    # 2. Format DRF Exceptions
    error_code = "UNKNOWN_ERROR"
    details = response.data

    if isinstance(exc, APIException):
        if hasattr(exc, "default_code"):
            error_code = str(exc.default_code).upper()
        else:
            error_code = exc.__class__.__name__.upper()

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "VALIDATION_ERROR"
            # Try to extract a specific error code if it's a simple validation error
            if hasattr(exc, "get_codes"):
                codes = exc.get_codes()
                if isinstance(codes, dict) and len(codes) == 1:
                    first_key = list(codes.keys())[0]
                    first_val = codes[first_key]
                    if isinstance(first_val, list) and len(first_val) == 1:
                        error_code = str(first_val[0]).upper()
                    elif isinstance(first_val, str):
                        error_code = first_val.upper()

        # If details is just a single 'detail' string, simplify the payload
        if isinstance(details, dict) and "detail" in details and len(details) == 1:
            details = details["detail"]
            if hasattr(exc, "get_codes"):
                codes = exc.get_codes()
                if isinstance(codes, str):
                    error_code = codes.upper()
                elif isinstance(codes, dict) and "detail" in codes:
                    error_code = str(codes["detail"]).upper()

    response.data = {"error_code": error_code, "details": details}

    return response
