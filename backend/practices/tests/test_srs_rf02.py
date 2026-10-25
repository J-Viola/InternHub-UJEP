from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from practices.serializers import ExternalPracticeSerializer, PracticeSerializer


class PracticeRF02SerializerTests(SimpleTestCase):
    def test_semester_accepts_only_zs_or_ls_and_is_optional(self):
        for semester in ("ZS", "LS"):
            serializer = PracticeSerializer(data={"semester": semester}, partial=True)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["semester"], semester)

        serializer = PracticeSerializer(data={"semester": "SS"}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("semester", serializer.errors)

        serializer = PracticeSerializer(data={}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_legacy_skills_list_is_normalized_to_technologies(self):
        serializer = PracticeSerializer(
            data={
                "skills": ["Python", "Django"],
                "start_date": (date.today() + timedelta(days=2)).strftime("%d.%m.%Y"),
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["skills"],
            {"technologies": ["Python", "Django"], "tools": [], "methodologies": []},
        )


class ExternalPracticeRF02SerializerTests(SimpleTestCase):
    def _data(self, **overrides):
        data = {
            "external_details_file": SimpleUploadedFile("detaily.pdf", b"%PDF-1.4 content", content_type="application/pdf"),
            "skills": ["Python", "Django"],
        }
        data.update(overrides)
        return data

    def test_legacy_skills_list_is_normalized(self):
        serializer = ExternalPracticeSerializer(data=self._data(), partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["skills"],
            {"technologies": ["Python", "Django"], "tools": [], "methodologies": []},
        )

    def test_semester_accepts_zs_and_ls_and_rejects_other_values(self):
        for semester in ("ZS", "LS"):
            serializer = ExternalPracticeSerializer(data=self._data(semester=semester), partial=True)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["semester"], semester)

        serializer = ExternalPracticeSerializer(data=self._data(semester="SS"), partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("semester", serializer.errors)
