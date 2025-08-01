"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from api.views import serve_user_file
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import settings
from .views import index

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/practices/", include("practices.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/documents/<path:path>/", serve_user_file, name="serve_user_file"),
    path("api/departments/", include("department.urls")),
    path("api/subjects/", include("subject.urls")),
]

# TODO: Remove this in production
if settings.DEBUG:
    urlpatterns += static(settings.STORAGE_URL, document_root=settings.STORAGE_URL)
