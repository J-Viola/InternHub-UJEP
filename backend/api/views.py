"""
Infrastructure views: file serving, health checks, utility endpoints.
"""

from pathlib import Path

from django.conf import settings
from django.core import management
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.file_access import (
    StorageAccess,
    canonical_rel_path,
    check_storage_access,
    rel_path_from_uri,
    user_can_access_storage_path,
)
from api.test_scenarios import ScenarioBuilder
from users.models import (
    ActionLog,
    EmployerProfile,
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


class ServeStorageFileView(APIView):
    """
    Serve a file from ``STORAGE_ROOT`` with authentication and path validation.

    A-25: oprávnění rozhoduje jediná funkce ``api.file_access.check_storage_access``
    (stejná jako v ``StorageAuthCheckView`` a ``DocumentPermissionMiddleware``):
      - Superuser → always allowed
      - CV / profilová fotka: owner / employer who received application / professor
        teaching the student's subject / department head
      - Practice docs: delegated to ``UploadedDocument.user_has_permission()``
      - Firemní loga: veřejná

    Replace ``/storage/`` direct Nginx serve with ``X-Accel-Redirect`` in production
    to bypass Django for the actual byte stream.
    """

    permission_classes = [IsAuthenticated]
    rel_prefix = ""

    # ── public API ──────────────────────────────────────────────────────

    def get(self, request, path):
        rel = self.rel_prefix + path
        file_path = self._resolve(rel)
        decision = check_storage_access(request.user, rel)
        if decision is StorageAccess.NOT_FOUND:
            raise Http404
        if decision is not StorageAccess.ALLOWED:
            raise PermissionDenied
        return FileResponse(open(file_path, "rb"), filename=file_path.name)

    # ── path resolution + security ──────────────────────────────────────

    def _resolve(self, rel: str) -> Path:
        """Resolve *rel* inside STORAGE_ROOT; raise Http404 on escape or missing file.

        Hledá i zdvojenou cestu ``storage/<rel>`` (``upload_to`` CV a obrázků obsahuje ``STORAGE_URL``).
        """
        root = Path(settings.STORAGE_ROOT).resolve()
        canonical = canonical_rel_path(rel)
        for candidate in (canonical, settings.STORAGE_URL.strip("/") + "/" + canonical):
            full = (root / candidate).resolve()
            if not full.is_relative_to(root):
                raise Http404
            if full.is_file():
                return full
        raise Http404


class ServeUserFileView(ServeStorageFileView):
    """Zpětně kompatibilní trasa ``/api/documents/<path>/`` (kořen ``documents/``)."""

    rel_prefix = "documents/"


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
    """Auth gate pro nginx ``auth_request`` na ``/storage/`` (A-01).

    Nginx předá původní URI v ``X-Original-URI``; stejná autorizační funkce jako
    ``ServeStorageFileView``. Chybějící hlavička, neznámý soubor, traversal i
    nedostatečné oprávnění → **403** (``auth_request`` rozumí jen 2xx/401/403,
    cokoli jiného by Nginx změnil na 500). Nepřihlášený → 401 (DRF).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        rel = rel_path_from_uri(request.META.get("HTTP_X_ORIGINAL_URI"))
        if rel is None or not user_can_access_storage_path(request.user, rel):
            return HttpResponse(status=403)
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
            from test_support.db_reset import reset_e2e_database

            reset_e2e_database(using="default")
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
                for scope in (
                    "anon",
                    "user",
                    "login",
                    "stag_ticket",
                    "password_reset",
                    "ares",
                ):
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
        stag_vy, _ = StagRole.objects.get_or_create(
            role="vy",
            defaults={"role_name": "Vyučující", "description": "Vyučující na katedře"},
        )

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
                UserSubject.objects.get_or_create(
                    user=student,
                    subject=first,
                    defaults={"role": UserSubjectType.Student},
                )


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
            {
                "status": "ok" if db_ok else "error",
                "db": "ok" if db_ok else "unavailable",
            },
            status=200 if db_ok else 503,
        )


class DashboardStatsView(APIView):
    """
    Monitoring dashboard stats endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from api.dashboard_service import DashboardService

        data = DashboardService.get_stats_for_user(request.user)
        return Response(data)


class DataExportView(APIView):
    """
    Bulk data export endpoint for practices.
    Pro >500 záznamů spouští asynchronní Celery task.
    """

    permission_classes = [IsAuthenticated]

    def perform_content_negotiation(self, request, force=False):
        """
        Export si řídí formát sám přes ``?format=csv|xlsx`` (vrací raw HttpResponse).

        DRF by jinak pro ``?format=csv`` hledal renderer s formátem 'csv' a vracel
        Http404 (žádný takový renderer není registrovaný). Vracíme výchozí renderer,
        aby DRF nenegocioval — formát zpracuje samotný view.
        """
        renderers = self.get_renderers()
        return (renderers[0], renderers[0].media_type)

    def get(self, request):
        from api.export_service import ExportService
        from student_practices.models import (
            StudentPractice,
            StudentPracticeWorkflowState,
        )

        try:
            params = getattr(request, "query_params", request.GET)
            fmt = str(params.get("format", "xlsx")).lower()
            year = params.get("year")
            state = params.get("workflow_state")
            subject_id = params.get("subject_id")
            employer_id = params.get("employer_id")
            institution = params.get("institution")

            # Fail-closed (BE-003): prázdný/neplatný stavový filtr se nikdy
            # neodhodí ve prospěch neomezeného exportu → 400, ne globální řádky.
            if state is not None:
                try:
                    state_value = int(str(state).strip())
                except (TypeError, ValueError):
                    state_value = None
                if state_value is None or StudentPracticeWorkflowState.get(state_value) is None:
                    return Response({"detail": "Neplatný filtr workflow_state."}, status=400)
                state = state_value

            filters = {
                "year": year,
                "workflow_state": state,
                "subject_id": subject_id,
                "employer_id": employer_id,
                "institution": institution,
            }

            # Role-based scoping: garant/profesor katedry → jen vlastní
            # department; organizace → vlastní praxe; student → PŘESNĚ jen
            # vlastní přihlášky (MAJOR-2); superuser → vše.
            user = request.user
            dept_ids, org_employer, owner_user = ExportService.get_scope_filters(user)

            # Fail-closed (BE-003): prázdný/žádný rozsah → 403, nikdy
            # globální export. (None, None, None) = superuser — jediný
            # neomezený rozsah.
            if dept_ids is None and org_employer is None and owner_user is None:
                pass  # superuser
            elif not dept_ids and org_employer is None and owner_user is None:
                return Response(
                    {"detail": "Pro váš účet neexistuje žádný exportní rozsah."},
                    status=403,
                )

            # Zjisti počet záznamů
            count = ExportService.get_count(filters, dept_ids=dept_ids, employer=org_employer, owner_user=owner_user)

            # Fail-closed (BE-003): žádné autorizované řádky → prázdná množina
            # = deny (403), ne prázdný „úspěch" a nikdy globální export.
            if count == 0:
                return Response(
                    {"detail": "Pro váš účet neexistuje žádný exportní rozsah."},
                    status=403,
                )

            # Pokud >500, deleguj na Celery task — scoping se aplikuje uvnitř tasku
            # (předává se user_id; viz api/tasks.py export_data_async).
            if count > 500:
                import uuid

                from api.tasks import export_data_async

                export_id = str(uuid.uuid4())
                export_data_async.delay(export_id, filters, fmt, user.pk)
                from django.core.cache import cache

                # TTL 7200: user_id cache musí přežít data cache (3600), jinak by
                # legitimní vlastník dostal 404 při zpožděném exportu (review A2).
                cache.set(f"export_{export_id}_user_id", user.pk, timeout=7200)
                # stavový marker pro DataExportStatusView (PENDING/SUCCESS/FAILURE)
                cache.set(f"export_{export_id}_status", "pending", timeout=3600)
                return Response(
                    {
                        "export_id": export_id,
                        "status": "processing",
                        "total_count": count,
                    }
                )

            # Synchronní export pro ≤500 záznamů (scope = stejný guard jako count)
            qs = StudentPractice.objects.filter(is_cancelled=False)
            qs = ExportService.apply_scope(qs, dept_ids, org_employer, owner_user)

            if year:
                qs = qs.filter(year=year)
            if state is not None:
                qs = qs.filter(workflow_state=state)
            if subject_id:
                qs = qs.filter(practice__subject_id=subject_id)
            if employer_id:
                qs = qs.filter(practice__employer_id=employer_id)
            if institution:
                qs = qs.filter(practice__employer__company_name__icontains=institution)

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

    odpověď ``{"state": "PENDING|SUCCESS|FAILURE",
    "download_url": ...}`` — download_url je naplněna cestou
    ``/api/export/download/{export_id}/`` při SUCCESS, jinak ``null``.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, export_id):
        from django.core.cache import cache

        # Ownership guard (BE-003 / MAJOR-3): stav ani download_url nesmí
        # uniknout bez doloženého vlastnictví — fail-closed. Povolen je jen
        # doložený vlastník žadatele nebo explicitně privilegovaná role
        # (staff/superuser); chybějící marker = vlastnictví nedoloženo → deny
        # se stejnou odpovědí jako u neexistujícího exportu (anti-enumerace).
        owner_id = cache.get(f"export_{export_id}_user_id")
        is_privileged = bool(request.user.is_staff or request.user.is_superuser)
        if owner_id is None:
            if not is_privileged:
                return Response(
                    {"export_id": export_id, "state": "PENDING", "download_url": None},
                    status=404,
                )
        elif owner_id != request.user.pk and not is_privileged:
            return Response(
                {"export_id": export_id, "state": "PENDING", "download_url": None},
                status=404,
            )

        cached = cache.get(f"export_{export_id}_status")

        if cached is None:
            # Neznámý / neexistující export — FE by takové id neměl pollovat.
            return Response(
                {"export_id": export_id, "state": "PENDING", "download_url": None},
                status=404,
            )

        if cached == "completed":
            return Response(
                {
                    "export_id": export_id,
                    "state": "SUCCESS",
                    "download_url": f"/api/export/download/{export_id}/",
                }
            )

        if isinstance(cached, str) and cached.startswith("error:"):
            return Response(
                {
                    "export_id": export_id,
                    "state": "FAILURE",
                    "download_url": None,
                    "detail": cached[len("error:") :].strip(),
                }
            )

        # Jakýkoli jiný stav (např. "pending") → export se stále zpracovává.
        return Response({"export_id": export_id, "state": "PENDING", "download_url": None})


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

        # ownership check — jen žádající uživatel nebo staff si smí stáhnout
        # hotový export (jiné entity nedostanou cizí data → 403/404).
        owner_id = cache.get(f"export_{export_id}_user_id")
        is_owner = owner_id is not None and owner_id == request.user.pk
        if not (is_owner or request.user.is_staff or request.user.is_superuser):
            return Response(
                {"export_id": export_id, "status": "not_found"},
                status=404,
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


class ActionLogListView(generics.ListAPIView):
    """Global audit log API — admin only."""

    permission_classes = [IsAdminUser]
    queryset = ActionLog.objects.all().order_by("-action_date")

    def get_serializer_class(self):
        from student_practices.serializers import ActionLogSerializer

        return ActionLogSerializer
