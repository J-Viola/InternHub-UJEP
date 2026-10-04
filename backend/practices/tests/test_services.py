from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from practices.models import Practice, PracticeWorkflowState
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
        self.practice.workflow_state = PracticeWorkflowState.OPEN_FOR_APPLICATIONS
        self.practice.start_date = date(2024, 1, 1)
        self.practice.end_date = date(2024, 6, 1)
        self.practice.available_positions = 5
        self.practice.contact_user = None
        self.practice.is_cancelled = False

    @patch("practices.services.NotificationService.notify_garant_new_application")
    @patch("practices.services.StudentPracticeSerializer")
    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.select_for_update")
    def test_apply_student_practice_success(self, mock_select_for_update, mock_sp_filter, mock_serializer, mock_garant_notify):
        # Setup mocks — active-app check returns False (no existing application)
        mock_sp_filter.return_value.exists.return_value = False
        # Capacity count returns 0 (below available_positions)
        mock_sp_filter.return_value.count.return_value = 0
        # select_for_update chain returns practice
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.first.return_value = self.practice
        mock_select_for_update.return_value = mock_queryset

        serializer_instance = mock_serializer.return_value
        serializer_instance.is_valid.return_value = True
        serializer_instance.data = {"id": 1, "status": "pending"}
        sp_mock = MagicMock(spec=StudentPractice)
        serializer_instance.save.return_value = sp_mock

        # Call service
        result = PracticeService.apply_student_practice(self.user, 1)

        # Assertions
        self.assertEqual(result, {"id": 1, "status": "pending"})
        mock_serializer.assert_called_once()
        # workflow_state should be set directly on the SP object
        sp_mock.save.assert_called_with(update_fields=["workflow_state"])
        # garant je notifikován o nové žádosti (in-app + e-mail metoda)
        mock_garant_notify.assert_called_once_with(sp_mock)

    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.select_for_update")
    def test_apply_student_practice_already_exists(self, mock_select_for_update, mock_sp_filter):
        # Active application exists, but capacity is not full
        # First exists() = unresolved_cancellation (is_cancelled=True) → False
        # Second exists() = existing_active (is_cancelled=False) → True
        mock_sp_filter.return_value.count.return_value = 0

        def exists_side_effect():
            if not hasattr(exists_side_effect, "call_count"):
                exists_side_effect.call_count = 0
            exists_side_effect.call_count += 1
            # First call is unresolved_cancellation (should be False)
            # Second call is existing_active (should be True)
            return exists_side_effect.call_count == 2

        mock_sp_filter.return_value.exists.side_effect = exists_side_effect
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.first.return_value = self.practice
        mock_select_for_update.return_value = mock_queryset

        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(self.user, 1)

        self.assertIn("ALREADY_APPLIED", str(cm.exception))

    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.select_for_update")
    def test_apply_student_practice_not_found(self, mock_select_for_update, mock_sp_filter):
        mock_sp_filter.return_value.exists.return_value = False
        mock_sp_filter.return_value.count.return_value = 0
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.first.return_value = None
        mock_select_for_update.return_value = mock_queryset

        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(self.user, 1)

        self.assertIn("NOT_FOUND", str(cm.exception))

    @patch("practices.services.StudentPracticeSerializer")
    @patch("practices.services.StudentPractice.objects.filter")
    @patch("practices.services.Practice.objects.select_for_update")
    def test_apply_student_practice_cancelled_practice(self, mock_select_for_update, mock_sp_filter, mock_serializer):
        """3.7: Cannot apply to a cancelled practice."""
        mock_sp_filter.return_value.exists.return_value = False
        mock_sp_filter.return_value.count.return_value = 0
        self.practice.is_cancelled = True
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.first.return_value = self.practice
        mock_select_for_update.return_value = mock_queryset

        with self.assertRaises(ValueError) as cm:
            PracticeService.apply_student_practice(self.user, 1)

        self.assertIn("PRACTICE_IS_CANCELLED", str(cm.exception))
