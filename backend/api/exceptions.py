from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler that handles ValueError and maps it to 400 Bad Request.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If response is None, then there's an unhandled exception
    if response is None:
        if isinstance(exc, ValueError):
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return response
