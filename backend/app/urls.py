from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api.views import (
    ActionLogListView,
    DashboardStatsView,
    DataExportDownloadView,
    DataExportStatusView,
    DataExportView,
    HealthCheckView,
    ServeStorageFileView,
    ServeUserFileView,
    StorageAuthCheckView,
    UniqueLocationsListView,
)

from . import settings
from .views import index

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/practices/", include("practices.urls")),
    path("api/departments/", include("department.urls")),
    path("api/subjects/", include("subject.urls")),
    path("api/export-data/", DataExportView.as_view(), name="data-export"),
    path("api/export/status/<str:export_id>/", DataExportStatusView.as_view(), name="export-status"),
    path("api/export/download/<str:export_id>/", DataExportDownloadView.as_view(), name="export-download"),
    path("api/student-practices/", include("student_practices.urls")),
    path("api/code-lists/locations/", UniqueLocationsListView.as_view()),
    path("api/documents/<path:path>/", ServeUserFileView.as_view()),
    path("api/files/<path:path>/", ServeStorageFileView.as_view()),
    path("api/auth/check/", StorageAuthCheckView.as_view()),
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/audit-logs/", ActionLogListView.as_view(), name="audit-logs"),
    # OpenAPI schema and Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    from api.views import TestResetDBView, TestScenarioView

    urlpatterns += [
        path("api/test/reset-db/", TestResetDBView.as_view(), name="test-reset-db"),
        path("api/test/scenario/<str:name>/", TestScenarioView.as_view(), name="test-scenario"),
    ]

# Serving media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
