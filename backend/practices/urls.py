from django.urls import include, path
from rest_framework import routers

from .views import ChangePendingView, PracticesForApprovingListView, PracticeViewSet, RunningPracticeListView

app_name = "practices"

router = routers.DefaultRouter()
router.register(r"practices", PracticeViewSet, basename="practice")
urlpatterns = [
    path("", include(router.urls)),
    path("running-practices/", RunningPracticeListView.as_view(), name="running-practices"),
    path("practices-for-approval/", PracticesForApprovingListView.as_view(), name="practices-for-approval"),
    path("<int:id>/change-pending/", ChangePendingView.as_view(), name="change-pending"),
]
