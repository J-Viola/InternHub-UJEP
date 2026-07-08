"""
Infrastructure views: file serving, health checks, utility endpoints.
"""

from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from student_practices.models import UploadedDocument
from users.models import (
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubjectType,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _media_rel(full_path: Path) -> str:
    """Strip MEDIA_ROOT prefix from *full_path* for DB exact-match lookups."""
    return str(full_path.relative_to(Path(settings.MEDIA_ROOT).resolve()))


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------------------------------------------------------------------
# Protected file serving  (CR-API-1 — path-traversal hardened)
# ---------------------------------------------------------------------------


class ServeUserFileView(APIView):
    """
    Serve user-uploaded documents with authentication and path validation.

    Permission model (fail-closed):
      - Superuser → always allowed
      - CV files:   owner / employer who received application / professor teaching the
                     student's subject / department head
      - Practice docs: delegated to ``UploadedDocument.user_has_permission()``

    Replace ``/storage/`` direct Nginx serve with ``X-Accel-Redirect`` in production
    to bypass Django for the actual byte stream.
    """

    permission_classes = [IsAuthenticated]

    # ── public API ──────────────────────────────────────────────────────

    def get(self, request, path):
        file_path = self._resolve(path)
        self._check_access(request.user, file_path, path)
        return FileResponse(open(file_path, "rb"), filename=file_path.name)

    # ── path resolution + security ──────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        """Resolve *path* inside STORAGE_ROOT/documents; raise Http404 on escape or missing file."""
        doc_root = Path(settings.STORAGE_ROOT) / "documents"
        full = (doc_root / path).resolve()
        if not full.is_relative_to(doc_root.resolve()):
            raise Http404
        if not full.is_file():
            raise Http404
        return full

    # ── access dispatch ─────────────────────────────────────────────────

    def _check_access(self, user, file_path: Path, path: str):
        """Enforce access or raise PermissionDenied / Http404."""
        if user.is_superuser:
            return

        rel = _media_rel(file_path)

        if "cvs/" in path:
            student = get_object_or_404(StudentUser, cv_file=rel)
            self._require_cv_access(user, student)
        else:
            doc = get_object_or_404(UploadedDocument, document=rel)
            if not doc.user_has_permission(user):
                raise PermissionDenied

    # ── CV access sub-checks ────────────────────────────────────────────

    def _require_cv_access(self, user, student):
        if student.user_id == user.user_id:
            return
        if isinstance(user, OrganizationUser) and self._employer_has_cv_access(user, student):
            return
        if isinstance(user, ProfessorUser) and self._professor_has_cv_access(user, student):
            return
        raise PermissionDenied

    @staticmethod
    def _employer_has_cv_access(user, student) -> bool:
        employer = getattr(user, "employer_profile", None)
        if not employer:
            return False
        return student.student_practices.filter(practice__employer=employer).exists()

    @staticmethod
    def _professor_has_cv_access(user, student) -> bool:
        if student.user_subjects.filter(
            subject__user_subjects__user=user,
            subject__user_subjects__role=UserSubjectType.Professor,
        ).exists():
            return True
        if user.department_role == DepartmentRole.HEAD:
            return student.user_subjects.filter(subject__department=user.department).exists()
        return False


# ---------------------------------------------------------------------------
# Utility views
# ---------------------------------------------------------------------------


class UniqueLocationsListView(APIView):
    """De-duplicated set of cities + addresses for the listing-page location filter."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get unique practice locations",
        tags=["Utils"],
        responses={200: OpenApiResponse(description="List of unique locations")},
    )
    def get(self, request):
        profiles = EmployerProfile.objects
        cities = profiles.exclude(city__isnull=True, city="").values_list("city", flat=True)
        addresses = profiles.exclude(address__isnull=True, address="").values_list("address", flat=True)
        return Response(sorted(set(cities) | set(addresses)))


class StorageAuthCheckView(APIView):
    """Lightweight auth gate used by nginx ``auth_request`` directive."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return HttpResponse(status=200)


class HealthCheckView(APIView):
    """
    K8s liveness/readiness probe.
    200 + ``{"db":"ok"}`` when DB reachable, 503 otherwise.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_ok = True
        except Exception:
            pass
        return JsonResponse(
            {"status": "ok" if db_ok else "error", "db": "ok" if db_ok else "unavailable"},
            status=200 if db_ok else 503,
        )
