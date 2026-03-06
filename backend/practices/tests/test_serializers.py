from datetime import date, timedelta

from django.test import TestCase

from practices.serializers import (
    EndDateRequestSerializer,
    PracticeApprovalStatusSerializer,
    PracticeSerializer,
)
from users.models import ApprovalStatus

# ===========================================================================
# PracticeSerializer — validate() date logic
# ===========================================================================


class PracticeSerializerValidationTests(TestCase):
    """
    Tests for PracticeSerializer.validate() which enforces:
      - start_date >= today
      - end_date >= start_date
    These run at the serializer level without hitting the DB.
    """

    def _run(self, start_delta, end_delta=None):
        """
        Runs serializer validation with start = today+start_delta and
        end = today+end_delta. Returns the serializer instance.
        """
        today = date.today()
        data = {
            "start_date": (today + timedelta(days=start_delta)).strftime("%d.%m.%Y"),
        }
        if end_delta is not None:
            data["end_date"] = (today + timedelta(days=end_delta)).strftime("%d.%m.%Y")

        s = PracticeSerializer(data=data, partial=True)
        s.is_valid()  # trigger validation; ignore field-level errors
        return s

    def test_valid_future_start_and_end(self):
        s = self._run(start_delta=5, end_delta=90)
        # Date validation should not add a non-field error
        self.assertNotIn("non_field_errors", s.errors)

    def test_start_date_in_past_raises_error(self):
        s = self._run(start_delta=-1, end_delta=10)
        errors = str(s.errors)
        self.assertIn("minulosti", errors)

    def test_end_date_before_start_raises_error(self):
        s = self._run(start_delta=10, end_delta=5)
        errors = str(s.errors)
        self.assertIn("ukončení", errors)

    def test_end_date_equal_to_start_is_valid(self):
        s = self._run(start_delta=5, end_delta=5)
        self.assertNotIn("non_field_errors", s.errors)

    def test_start_is_today_is_valid(self):
        # validate() checks start < today (strict), so today itself is allowed
        s = self._run(start_delta=0, end_delta=10)
        self.assertNotIn("non_field_errors", s.errors)


# ===========================================================================
# PracticeApprovalStatusSerializer
# ===========================================================================


class PracticeApprovalStatusSerializerTests(TestCase):
    def test_approved_status_accepted(self):
        # choices are the display labels, not integer values
        approved_label = dict(ApprovalStatus.choices()).get(ApprovalStatus.APPROVED)
        s = PracticeApprovalStatusSerializer(data={"approval_status": approved_label})
        self.assertTrue(s.is_valid(), s.errors)

    def test_rejected_status_accepted(self):
        rejected_label = dict(ApprovalStatus.choices()).get(ApprovalStatus.REJECTED)
        s = PracticeApprovalStatusSerializer(data={"approval_status": rejected_label})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_status_string_rejected(self):
        s = PracticeApprovalStatusSerializer(data={"approval_status": "nonsense"})
        self.assertFalse(s.is_valid())
        self.assertIn("approval_status", s.errors)

    def test_missing_status_rejected(self):
        s = PracticeApprovalStatusSerializer(data={})
        self.assertFalse(s.is_valid())
        self.assertIn("approval_status", s.errors)


# ===========================================================================
# EndDateRequestSerializer
# ===========================================================================


class EndDateRequestSerializerTests(TestCase):
    def test_valid_data_passes(self):
        today = date.today()
        s = EndDateRequestSerializer(
            data={
                "start_date": today.strftime("%d.%m.%Y"),
                "coefficient": 1.0,
            }
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_missing_start_date_rejected(self):
        s = EndDateRequestSerializer(data={"coefficient": 1.0})
        self.assertFalse(s.is_valid())
        self.assertIn("start_date", s.errors)

    def test_missing_coefficient_rejected(self):
        s = EndDateRequestSerializer(data={"start_date": date.today().strftime("%d.%m.%Y")})
        self.assertFalse(s.is_valid())
        self.assertIn("coefficient", s.errors)

    def test_invalid_coefficient_type_rejected(self):
        s = EndDateRequestSerializer(
            data={
                "start_date": date.today().strftime("%d.%m.%Y"),
                "coefficient": "not-a-number",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("coefficient", s.errors)
