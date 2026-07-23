"""
Infrastructure views: file serving, health checks, utility endpoints.
"""

from pathlib import Path

from django.conf import settings
from django.core import management
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.test_scenarios import ScenarioBuilder
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


# ---------------------------------------------------------------------------
# Test utility  (only available when DEBUG=True)

# ---------------------------------------------------------------------------


class TestResetDBView(APIView):
    """
    Reset the database to a known seed state for E2E testing.

    **Only available when ``DEBUG=True``** — returns 403 in production.
    Flushes all data and re-runs ``seed_db`` to get reproducible demo data.

    Usage::

        POST /api/test/reset-db/

    Response::

        {"status": "ok", "seeded": true}
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth needed in DEBUG mode
    throttle_classes = []  # exempt from all throttling for test runs

    def post(self, request):
        if not settings.DEBUG:
            return JsonResponse({"error": "Test endpoint is only available in DEBUG mode"}, status=403)

        # Prevent accidental use when STAG is configured for real
        if not settings.STAG_MOCK:
            return JsonResponse({"error": "Test endpoint requires STAG_MOCK=True"}, status=400)

        try:
            management.call_command("flush", "--noinput", interactive=False)
            management.call_command("seed_db")
            self._create_e2e_test_users()

            # Disable token rotation so the SAME refresh token works across
            # multiple Playwright test contexts (each loads storage state with
            # the same cookie and calls refreshUX on mount).
            from django.conf import settings as dj_settings

            if hasattr(dj_settings, "SIMPLE_JWT"):
                dj_settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] = False
                dj_settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = False

            # Reset throttle cache so previously accumulated counters don't block requests
            from django.core.cache import cache

            cache.clear()

            # Lift all throttle limits for E2E test runs — many page loads & API
            # calls in quick succession would otherwise hit production-safe limits.
            if "DEFAULT_THROTTLE_RATES" in dj_settings.REST_FRAMEWORK:
                for scope in ("anon", "user", "login", "stag_ticket", "password_reset", "ares"):
                    dj_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope] = "100000/hour"

            return JsonResponse({"status": "ok", "seeded": True})
        except Exception as e:
            return JsonResponse({"status": "error", "detail": str(e)}, status=500)

    def _create_e2e_test_users(self):
        """Create professor and student users needed by E2E tests."""
        from django.contrib.auth.hashers import make_password

        from department.models import Department
        from users.models import (
            ProfessorUser,
            StagRole,
            StudentUser,
            User,
            UserSubject,
            UserSubjectType,
        )

        pw = make_password("password123")
        dept = Department.objects.first()
        stag_st, _ = StagRole.objects.get_or_create(role="st", defaults={"role_name": "Student", "description": "Student VŠ"})
        stag_vy, _ = StagRole.objects.get_or_create(role="vy", defaults={"role_name": "Vyučující", "description": "Vyučující na katedře"})

        if not User.objects.filter(email="professor@ujep.cz").exists():
            professor = ProfessorUser.objects.create(
                email="professor@ujep.cz",
                password=pw,
                first_name="Petr",
                last_name="Vomáčka",
                username="professor@ujep.cz",
                is_active=True,
                stag_role=stag_vy,
                department=dept,
                # Intentionally NOT setting department_role=HEAD
                # so that User.role returns "vy" (VY) = profesor role
                # Frontend UserObj.isProfessor() then matches correctly
                # and uses professorDict instead of departmentDict
                ucit_idno="654321",
            )
            # Link professor to subjects if any exist
            from subject.models import Subject

            for subj in Subject.objects.all():
                UserSubject.objects.get_or_create(
                    user=professor,
                    subject=subj,
                    defaults={"role": UserSubjectType.Professor},
                )

        if not User.objects.filter(email="tsedlacek@example.org").exists():
            student = StudentUser.objects.create(
                email="tsedlacek@example.org",
                password=pw,
                first_name="Ignác",
                last_name="Sedláček",
                username="tsedlacek@example.org",
                is_active=True,
                stag_role=stag_st,
                os_cislo="S12345",
                field_of_study="Informatika",
                year_of_study=3,
                city="Ústí nad Labem",
                skills=["Python", "React", "SQL"],
            )
            # Link student to first subject
            from subject.models import Subject

            first = Subject.objects.first()
            if first:
                UserSubject.objects.get_or_create(user=student, subject=first, defaults={"role": UserSubjectType.Student})


class TestScenarioView(APIView):
    """
    Prepare a specific database scenario for E2E tests.

    **Only available when ``DEBUG=True``** — returns 403 in production.

    Usage::

        POST /api/test/scenario/{name}/

    Available scenarios:

        student-has-applications  — student with an application
        student-has-documents     — student with application + documents
        invitation-exists         — employer invitation to student
        practice-has-favorites    — student favorited a practice
        practice-pending-approval — practice with PENDING status
        application-ready         — practice + application for company approval
        capacity-full             — practice with 1 spot, 1 approved student
        dual-approval-completed   — fully approved StudentPractice
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth needed in DEBUG mode
    throttle_classes = []  # exempt from all throttling for test runs

    def post(self, request, name):
        if not settings.DEBUG:
            return JsonResponse({"error": "Only available in DEBUG mode"}, status=403)
        if not settings.STAG_MOCK:
            return JsonResponse({"error": "Requires STAG_MOCK=True"}, status=400)

        builder = ScenarioBuilder()
        scenarios = {
            "student-has-applications": builder.student_has_applications,
            "student-has-documents": builder.student_has_documents,
            "invitation-exists": builder.invitation_exists,
            "practice-has-favorites": builder.practice_has_favorites,
            "practice-pending-approval": builder.practice_pending_approval,
            "application-ready": builder.application_ready,
            "capacity-full": builder.capacity_full,
            "dual-approval-completed": builder.dual_approval_completed,
        }

        handler = scenarios.get(name)
        if not handler:
            return JsonResponse(
                {
                    "error": f"Unknown scenario: {name}",
                    "available": list(scenarios.keys()),
                },
                status=400,
            )

        try:
            result = handler()
            return JsonResponse({"status": "ok", "scenario": name, "result": result})
        except Exception as e:
            return JsonResponse({"status": "error", "detail": str(e)}, status=500)


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


class DashboardStatsView(APIView):
    """
    Monitoring dashboard stats endpoint (Item 2.5).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from api.dashboard_service import DashboardService

        data = DashboardService.get_stats_for_user(request.user)
        return Response(data)


class DataExportView(APIView):
    """
    Bulk data export endpoint for practices (Item 2.3).
    Pro >500 záznamů spouští asynchronní Celery task.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from api.export_service import ExportService
        from student_practices.models import StudentPractice

        try:
            params = getattr(request, "query_params", request.GET)
            fmt = str(params.get("format", "xlsx")).lower()
            year = params.get("year")
            state = params.get("workflow_state")
            subject_id = params.get("subject_id")

            filters = {
                "year": year,
                "workflow_state": state,
                "subject_id": subject_id,
            }

            # Department scoping for count (same as sync query below)
            user = request.user
            dept_ids = None
            if not user.is_superuser and hasattr(user, "user_subjects"):
                dept_ids = list(user.user_subjects.values_list("subject__department_id", flat=True))
            org_employer = getattr(user, "employer_profile", None)

            # Zjisti počet záznamů
            count = ExportService.get_count(filters, dept_ids=dept_ids, employer=org_employer)

            # Pokud >500, deleguj na Celery task (NOTE: async export may lack user-level
            # scoping — consider admin-only async or passing scoped filters).
            if count > 500:
                import uuid

                from api.tasks import export_data_async

                export_id = str(uuid.uuid4())
                export_data_async.delay(export_id, filters, fmt)
                return Response(
                    {
                        "export_id": export_id,
                        "status": "processing",
                        "total_count": count,
                    }
                )

            # Synchronní export pro ≤500 záznamů
            qs = StudentPractice.objects.filter(is_cancelled=False)

            # Department scoping: non-superusers see only their own department's practices
            user = request.user
            if not user.is_superuser and hasattr(user, "user_subjects"):
                dept_ids = user.user_subjects.values_list("subject__department_id", flat=True)
                if dept_ids:
                    qs = qs.filter(practice__subject__department_id__in=dept_ids)

            # For organization users, scope to their own employer's practices
            if hasattr(user, "employer_profile") and user.employer_profile:
                qs = qs.filter(practice__employer=user.employer_profile)

            if year:
                qs = qs.filter(year=year)
            if state is not None:
                qs = qs.filter(workflow_state=state)
            if subject_id:
                qs = qs.filter(practice__subject_id=subject_id)

            if fmt == "csv":
                csv_content = ExportService.generate_csv(qs)
                response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
                response["Content-Disposition"] = 'attachment; filename="praxe_export.csv"'
                return response
            else:
                xlsx_bytes = ExportService.generate_xlsx(qs)
                response = HttpResponse(
                    xlsx_bytes,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = 'attachment; filename="praxe_export.xlsx"'
                return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class DataExportStatusView(APIView):
    """
    Endpoint pro kontrolu stavu asynchronního exportu (polling).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, export_id):
        from django.core.cache import cache

        status = cache.get(f"export_{export_id}_status")
        if status is None:
            return Response({"export_id": export_id, "status": "not_found"}, status=404)
        return Response({"export_id": export_id, "status": status})


class DataExportDownloadView(APIView):
    """
    Endpoint pro stažení hotového asynchronního exportu.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, export_id):
        from django.core.cache import cache

        status = cache.get(f"export_{export_id}_status")
        if status != "completed":
            return Response(
                {
                    "export_id": export_id,
                    "status": status if status else "not_found",
                },
                status=404 if status is None else 400,
            )

        data = cache.get(f"export_{export_id}")
        fmt = cache.get(f"export_{export_id}_fmt", "xlsx")

        if fmt == "csv":
            response = HttpResponse(data, content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="praxe_export.csv"'
        else:
            response = HttpResponse(
                data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="praxe_export.xlsx"'
        return response
