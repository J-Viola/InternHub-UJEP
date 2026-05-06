import base64
import uuid
from datetime import datetime

import bleach
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from practices.messages import PracticeMessages


def sanitize_html(text):
    if not text or not isinstance(text, str):
        return text
    return bleach.clean(text, tags=[], attributes={}, strip=True)


class SanitizedCharField(serializers.CharField):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return sanitize_html(data)


def can_manage_practice(user, student_practice) -> dict:
    """
    Centralized permission check for a user relative to a StudentPractice.
    Returns a dict with role flags: {is_professor, is_org, is_admin}.
    Raises ValueError if the user has no authorization.
    """
    from users.models import (
        DepartmentRole,
        OrganizationUser,
        ProfessorUser,
        UserSubjectType,
    )

    is_professor = isinstance(user, ProfessorUser)
    is_org = isinstance(user, OrganizationUser)
    is_admin = user.is_superuser

    if is_professor and not is_admin:
        subject = student_practice.practice.subject
        is_head = user.department_role == DepartmentRole.HEAD and user.department == subject.department
        is_manager = subject.subject_manager == user
        is_teacher = user.user_subjects.filter(subject=subject, role=UserSubjectType.Professor).exists()
        if not (is_head or is_manager or is_teacher):
            is_professor = False

    if is_org and not is_admin:
        if student_practice.practice.employer != getattr(user, "employer_profile", None):
            is_org = False

    if not (is_professor or is_org or is_admin):
        raise PermissionDenied()

    return {"is_professor": is_professor, "is_org": is_org, "is_admin": is_admin}


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
