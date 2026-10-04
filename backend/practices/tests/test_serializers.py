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
        self.assertIn("DATE_IN_PAST", errors)

    def test_end_date_before_start_raises_error(self):
        s = self._run(start_delta=10, end_delta=5)
        errors = str(s.errors)
        self.assertIn("END_DATE_BEFORE_START", errors)

    def test_end_date_equal_to_start_is_valid(self):
        s = self._run(start_delta=5, end_delta=5)
        self.assertNotIn("non_field_errors", s.errors)

    def test_start_is_today_is_valid(self):
        # validate() checks start < today (strict), so today itself is allowed
        s = self._run(start_delta=0, end_delta=10)
        self.assertNotIn("non_field_errors", s.errors)


class PracticeSerializerRequiredFieldsTests(TestCase):
    """mentor_name a contact_email jsou povinné při create/update nabídky."""

    def test_mentor_and_contact_email_required_on_create(self):
        s = PracticeSerializer(
            data={
                "title": "Nová stáž",
                "description": "Popis",
                "responsibilities": "Odpovědnosti",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("mentor_name", s.errors)
        self.assertIn("contact_email", s.errors)

    def test_mentor_and_contact_email_reject_blank_on_create(self):
        s = PracticeSerializer(
            data={
                "title": "Nová stáž",
                "description": "Popis",
                "responsibilities": "Odpovědnosti",
                "mentor_name": "",
                "contact_email": "",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("mentor_name", s.errors)
        self.assertIn("contact_email", s.errors)

    def test_region_optional(self):
        """Region není povinný — prázdná hodnota je povolená."""
        from datetime import date, timedelta

        today = date.today()
        s = PracticeSerializer(
            data={
                "title": "Nová stáž",
                "description": "Popis",
                "responsibilities": "Odpovědnosti",
                "mentor_name": "Jan Mentor",
                "contact_email": "mentor@firma.cz",
                "start_date": (today + timedelta(days=10)).strftime("%d.%m.%Y"),
            },
            partial=True,
        )
        # partial=True → required pole se neenforcejí; region prázdný nesmí hodit chybu
        s.is_valid()
        self.assertNotIn("region", s.errors)


class ExternalPracticeSerializerTests(TestCase):
    """příloha s detaily praxe povinná a ve validním formátu."""

    def _base_data(self):
        from datetime import date, timedelta

        today = date.today()
        return {
            "employer_name": "Firma s.r.o.",
            "title": "Externí praxe",
            "description": "Popis",
            "start_date": (today + timedelta(days=10)).strftime("%d.%m.%Y"),
        }

    def test_external_details_file_required(self):
        from practices.serializers import ExternalPracticeSerializer

        s = ExternalPracticeSerializer(data=self._base_data())
        self.assertFalse(s.is_valid())
        self.assertIn("external_details_file", s.errors)

    def test_external_details_file_rejects_wrong_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from practices.serializers import ExternalPracticeSerializer

        data = self._base_data()
        data["external_details_file"] = SimpleUploadedFile("detaily.txt", b"text content", content_type="text/plain")
        s = ExternalPracticeSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("external_details_file", s.errors)

    def test_external_details_file_accepts_pdf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from practices.serializers import ExternalPracticeSerializer

        data = self._base_data()
        data["external_details_file"] = SimpleUploadedFile("detaily.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        s = ExternalPracticeSerializer(data=data)
        s.is_valid()
        # Validace souboru projde (zbývající chyby jsou jen chybějící povinná pole jako subject_id)
        self.assertNotIn("external_details_file", s.errors)


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

    def test_missing_coefficient_accepted(self):
        """Coefficient is deprecated and no longer required — use min_hours instead."""
        s = EndDateRequestSerializer(data={"start_date": date.today().strftime("%d.%m.%Y")})
        self.assertTrue(s.is_valid(), "Coefficient is no longer required")

    def test_invalid_coefficient_type_rejected(self):
        s = EndDateRequestSerializer(
            data={
                "start_date": date.today().strftime("%d.%m.%Y"),
                "coefficient": "not-a-number",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("coefficient", s.errors)
