from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.views import APIView

from api.exceptions import custom_exception_handler


class TestExceptionView(APIView):
    def get(self, request):
        raise ValueError("Test Value Error")


class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_value_error_handler(self):
        # Simulate an exception in a view context
        # view = TestExceptionView.as_view()
        # request = self.factory.get("/")

        # Since middleware/exception handler is usually processed by DRF's dispatch,
        # we can call the handler directly or rely on integration test if we registered it.
        # Calling directly is better for unit testing the handler logic.

        exception = ValueError("Test Error")
        context = {}  # DRF context usually has view, args, kwargs

        response = custom_exception_handler(exception, context)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "Test Error")
        self.assertEqual(response.data["details"], "Test Error")

    def test_standard_exception_handler_passthrough(self):
        # Test that standard DRF exceptions (like validation error) are still handled
        from rest_framework.exceptions import ValidationError

        exception = ValidationError("Validation Failed")
        context = {}

        response = custom_exception_handler(exception, context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # DRF standard handler returns list/dict for ValidationError, structure depends on DRF version/settings
        # But response should exist.
