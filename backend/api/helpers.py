from datetime import datetime

from rest_framework import serializers


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
            raise serializers.ValidationError("Invalid date format. Use DD.MM.YYYY")
