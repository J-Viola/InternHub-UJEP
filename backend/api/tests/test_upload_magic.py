import io
import zipfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from api.validators import validate_file_content


class UploadMagicValidationTests(SimpleTestCase):
    def test_rejects_fake_pdf(self):
        with self.assertRaises(ValidationError):
            validate_file_content(SimpleUploadedFile("fake.pdf", b"not a pdf"))

    def test_accepts_pdf_signature(self):
        upload = SimpleUploadedFile("valid.pdf", b"%PDF-1.7 test")
        validate_file_content(upload)
        self.assertEqual(upload.read(4), b"%PDF")

    def test_rejects_fake_docx(self):
        with self.assertRaises(ValidationError):
            validate_file_content(SimpleUploadedFile("fake.docx", b"not a zip"))

    def test_accepts_docx_with_word_document(self):
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr("word/document.xml", "<document/>")
        upload = SimpleUploadedFile("valid.docx", content.getvalue())
        validate_file_content(upload)
        self.assertEqual(upload.read(2), b"PK")
