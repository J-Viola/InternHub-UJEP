from datetime import datetime

from rest_framework import serializers


class FormattedDateField(serializers.DateField):
    # Metoda pro převod data na string ve formátu DD-MM-YYYY při serializaci
    def to_representation(self, value):
        if value:
            return value.strftime("%d.%m.%Y")
        return None
        # Metoda pro převod stringu na datum při deserializaci

    def to_internal_value(self, value):
        if value:
            if isinstance(value, datetime):
                return value.date()
            try:
                return datetime.strptime(value, "%d.%m.%Y").date()
            except ValueError:
                raise serializers.ValidationError("Invalid date format. Use DD.MM.YYYY")
        return None
