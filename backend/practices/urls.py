from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminPracticesListView,
    CancelPracticeView,
    CloseApplicationsView,
    EmployerPracticeViewSet,
    ExternalPracticeView,
    GetEndDateView,
    StaffPracticeViewSet,
    StudentPracticeViewSet,
    TransitionPracticeView,
)

app_name = "practices"

student_router = routers.DefaultRouter()
student_router.register(r"student", StudentPracticeViewSet, basename="student-practices")

employer_router = routers.DefaultRouter()
employer_router.register(r"employer", EmployerPracticeViewSet, basename="employer-practices")

staff_router = routers.DefaultRouter()
staff_router.register(r"staff", StaffPracticeViewSet, basename="staff-practices")


urlpatterns = [
    # Utils
    path("get-end-date/", GetEndDateView.as_view(), name="get-end-date"),
    # Admin
    path("admin-practices/", AdminPracticesListView.as_view(), name="admin-practices"),
    # State machine endpoints
    path("<int:pk>/transition/", TransitionPracticeView.as_view(), name="practice-transition"),
    path("<int:pk>/cancel/", CancelPracticeView.as_view(), name="practice-cancel"),
    path("<int:pk>/close-applications/", CloseApplicationsView.as_view(), name="practice-close-applications"),
    path("external/", ExternalPracticeView.as_view(), name="practice-external"),
    # API Routers
    path("", include(student_router.urls)),
    path("", include(employer_router.urls)),
    path("", include(staff_router.urls)),
]
