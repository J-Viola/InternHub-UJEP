from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from practices.models import Practice
from practices.services import PracticeService
from student_practices.models import StudentPractice
from users.models import StudentUser


class PracticeServiceTests(TestCase):
    def setUp(self):
        self.user = MagicMock(spec=StudentUser)
        self.user.pk = 1

        self.practice = MagicMock(spec=Practice)
        self.practice.practice_id = 1
        self.practice.is_active = True
        self.practice.start_date = date(2024, 1, 1)
        self.practice.end_date = date(2024, 6, 1)

    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.filter")
    @patch("practices.services.StudentPracticeSerializer")
    def test_apply_student_practice_success(self, mock_serializer, mock_practice_filter, mock_sp_filter):
        # Setup mocks
        mock_sp_filter.return_value.exists.return_value = False
        mock_practice_filter.return_value.first.return_value = self.practice

        serializer_instance = mock_serializer.return_value
        serializer_instance.is_valid.return_value = True
        serializer_instance.save.return_value = MagicMock(spec=StudentPractice)
        serializer_instance.data = {"id": 1, "status": "pending"}

        # Call service
        result = PracticeService.apply_student_practice(self.user, 1)

        # Assertions
        self.assertEqual(result, {"id": 1, "status": "pending"})
        mock_serializer.assert_called_once()

    @patch("practices.services.StudentPractice.objects.filter")
    def test_apply_student_practice_already_exists(self, mock_sp_filter):
        mock_sp_filter.return_value.exists.return_value = True

        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(self.user, 1)

        self.assertIn("ALREADY_APPLIED", str(cm.exception))

    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.filter")
    def test_apply_student_practice_not_found(self, mock_practice_filter, mock_sp_filter):
        mock_sp_filter.return_value.exists.return_value = False
        mock_practice_filter.return_value.first.return_value = None

        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(self.user, 1)

        self.assertIn("PRACTICE_NOT_FOUND", str(cm.exception))
