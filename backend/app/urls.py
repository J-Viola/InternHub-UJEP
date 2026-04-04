from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views import StorageAuthCheckView, UniqueLocationsListView, serve_user_file

from . import settings
from .views import index

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/practices/", include("practices.urls")),
    path("api/departments/", include("department.urls")),
    path("api/subjects/", include("subject.urls")),
    path("api/student-practices/", include("student_practices.urls")),
    path("api/code-lists/locations/", UniqueLocationsListView.as_view()),
    path("api/documents/<path:path>/", serve_user_file),
    path("api/auth/check/", StorageAuthCheckView.as_view()),
]

if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]

# Serving media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
