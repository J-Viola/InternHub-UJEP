"""A-25 — jediná autorizace přístupu k souborům v ``/storage/``.

Funkci ``check_storage_access`` volají všichni tři strážci stejně:
``ServeUserFileView`` (API), ``StorageAuthCheckView`` (Nginx ``auth_request``)
i ``DocumentPermissionMiddleware`` (Django ``static()`` ve vývoji).
Referenční pravidla jsou ta z ``ServeUserFileView`` (BP).

Pravidla podle typu souboru (cesta relativně ke ``STORAGE_ROOT``):

- ``documents/cvs/…``  — vlastník, zaměstnavatel s přihláškou studenta,
  vyučující předmětu studenta, vedoucí katedry,
- ``documents/…``      — ``UploadedDocument.user_has_permission()``,
- ``images/profiles/…``— stejně jako CV (osobní údaje studenta),
- ``images/logos/…``   — veřejné (logo firmy je součástí nabídky),
- cokoli jiného        — zamítnuto (fail-closed).

Superuživatel smí vše.
"""

from __future__ import annotations

import enum
import posixpath
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings

from student_practices.models import UploadedDocument
from users.models import (
    DepartmentRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubjectType,
)


class StorageAccess(enum.Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    NOT_FOUND = "not_found"


def _storage_prefix() -> str:
    return "/" + settings.STORAGE_URL.strip("/") + "/"


def canonical_rel_path(rel_path: str) -> str:
    """Odstraní zdvojený prefix ``storage/``.

    ``upload_to`` u CV a obrázků obsahuje ``STORAGE_URL``, takže jméno souboru v DB
    i cesta na disku začínají ``storage/`` navíc (``/storage/storage/documents/cvs/…``).
    """
    prefix = settings.STORAGE_URL.strip("/") + "/"
    while rel_path.startswith(prefix):
        rel_path = rel_path[len(prefix) :]
    return rel_path


def rel_path_from_uri(raw_uri: str | None) -> str | None:
    """Z ``X-Original-URI`` vyrobí bezpečnou cestu relativní ke ``/storage/``.

    Vrací ``None`` při chybějící hlavičce, jiném prefixu, traversalu (``..``,
    ``%2e%2e``, dvojité lomítko, zpětné lomítko, NUL) nebo úniku ze ``STORAGE_ROOT``.
    """
    if not raw_uri:
        return None
    path = urlsplit(raw_uri).path
    decoded = unquote(path)
    if "\x00" in decoded or "\\" in decoded or "%" in decoded:
        return None  # NUL, zpětné lomítko, dvojí kódování
    if posixpath.normpath(decoded) != decoded.rstrip("/") and decoded != "/":
        return None  # `..`, `.`, `//`
    if any(part in ("", ".", "..") for part in decoded.strip("/").split("/")):
        return None
    prefix = _storage_prefix()
    if not decoded.startswith(prefix) or len(decoded) == len(prefix):
        return None
    rel = decoded[len(prefix) :]
    root = Path(settings.STORAGE_ROOT).resolve()
    if not (root / rel).resolve().is_relative_to(root):
        return None
    return rel


def _db_names(canonical: str) -> list[str]:
    """Jména, pod kterými může být soubor v DB (s ``storage/`` prefixem i bez)."""
    return [canonical, settings.STORAGE_URL.strip("/") + "/" + canonical]


def _employer_has_access(user, student) -> bool:
    employer = getattr(user, "employer_profile", None)
    if not employer:
        return False
    return student.student_practices.filter(practice__employer=employer).exists()


def _professor_has_access(user, student) -> bool:
    # Jen aktivní vazby obou stran (synchronizace STAG odebrané vazby deaktivuje, nemaže).
    if student.user_subjects.filter(
        is_active=True,
        subject__user_subjects__user=user,
        subject__user_subjects__role=UserSubjectType.Professor,
        subject__user_subjects__is_active=True,
    ).exists():
        return True
    if user.department_role == DepartmentRole.HEAD or user.is_garant_praxe:
        return student.user_subjects.filter(is_active=True, subject__department=user.department).exists()
    return False


def user_can_see_student_private_file(user, student) -> bool:
    """CV a profilová fotka: vlastník, zaměstnavatel s přihláškou, vyučující, vedoucí katedry."""
    if student.user_id == user.user_id:
        return True
    if isinstance(user, OrganizationUser) and _employer_has_access(user, student):
        return True
    return bool(isinstance(user, ProfessorUser) and _professor_has_access(user, student))


def _decide_for_students(user, students) -> StorageAccess:
    """Rozhodnutí pro soubor patřící studentům (jméno s ``storage/`` prefixem i bez).

    Kolidují-li obě varianty jména u různých studentů, nelze určit, který fyzický soubor se vydá —
    přístup se povolí jen tehdy, smí-li uživatel vidět VŠECHNY dotčené studenty.
    """
    students = list(students)
    if not students:
        return StorageAccess.NOT_FOUND
    return StorageAccess.ALLOWED if all(user_can_see_student_private_file(user, st) for st in students) else StorageAccess.DENIED


def check_storage_access(user, rel_path: str) -> StorageAccess:
    """Rozhodne o přístupu uživatele k souboru ``rel_path`` (relativně ke ``STORAGE_ROOT``)."""
    if not user or not getattr(user, "is_authenticated", False):
        return StorageAccess.DENIED
    if user.is_superuser:
        return StorageAccess.ALLOWED
    canonical = canonical_rel_path(rel_path)
    names = _db_names(canonical)

    if canonical.startswith("documents/cvs/"):
        return _decide_for_students(user, StudentUser.objects.filter(cv_file__in=names))

    if canonical.startswith("documents/"):
        doc = UploadedDocument.objects.filter(document=canonical).first()
        if doc is None:
            return StorageAccess.NOT_FOUND
        return StorageAccess.ALLOWED if doc.user_has_permission(user) else StorageAccess.DENIED

    if canonical.startswith("images/profiles/"):
        return _decide_for_students(user, StudentUser.objects.filter(profile_picture__in=names))

    if canonical.startswith("images/logos/"):
        return StorageAccess.ALLOWED

    return StorageAccess.DENIED


def user_can_access_storage_path(user, rel_path: str) -> bool:
    return check_storage_access(user, rel_path) is StorageAccess.ALLOWED
