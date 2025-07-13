from django.urls import include, path
from rest_framework import routers

from .views import PracticeViewSet, RunningPracticeListView

# from rest_framework_simplejwt.views import TokenRefreshView


app_name = "practices"

router = routers.DefaultRouter()
router.register(r"practices", PracticeViewSet, basename="practice")
urlpatterns = [
    path("", include(router.urls)),
    path("running-practices/", RunningPracticeListView.as_view(), name="running-practices"),
]
