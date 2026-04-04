import base64
import uuid
from datetime import datetime

import bleach
from django.core.files.base import ContentFile
from rest_framework import serializers

from practices.messages import PracticeMessages


def sanitize_html(text):
    if not text or not isinstance(text, str):
        return text
    return bleach.clean(text, tags=[], attributes={}, strip=True)


class SanitizedCharField(serializers.CharField):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return sanitize_html(data)


class FormattedDateField(serializers.DateField):
    """Custom date field that formats dates as DD.MM.YYYY"""

    def to_representation(self, value):
        """Convert date to DD.MM.YYYY format for serialization"""
        return value.strftime("%d.%m.%Y") if value else None

    def to_internal_value(self, value):
        """Convert string to date for deserialization"""
        if not value:
            return None

        if isinstance(value, datetime):
            return value.date()

        try:
            return datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise serializers.ValidationError(PracticeMessages.INVALID_DATE_FORMAT)


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads as b64 encoded strings.
    """

    def to_internal_value(self, data):
        # Check if this is a base64 string
        if isinstance(data, str) and data.startswith("data:image"):
            # base64 encoded image - decode
            try:
                format_part, imgstr = data.split(";base64,")
                ext = format_part.split("/")[-1]

                # Generate a random name
                file_name = f"{uuid.uuid4()}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=file_name)
            except (ValueError, IndexError):
                raise serializers.ValidationError(PracticeMessages.INVALID_IMAGE_DATA)

        return super().to_internal_value(data)
