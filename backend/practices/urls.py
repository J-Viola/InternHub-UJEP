from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminPracticesListView,
    EmployerPracticeViewSet,
    GetEndDateView,
    StaffPracticeViewSet,
    StudentPracticeViewSet,
)

app_name = "practices"

student_router = routers.DefaultRouter()
student_router.register(
    r"student", StudentPracticeViewSet, basename="student-practices"
)

employer_router = routers.DefaultRouter()
employer_router.register(
    r"employer", EmployerPracticeViewSet, basename="employer-practices"
)

staff_router = routers.DefaultRouter()
staff_router.register(r"staff", StaffPracticeViewSet, basename="staff-practices")


urlpatterns = [
    # Utils
    path("get-end-date/", GetEndDateView.as_view(), name="get-end-date"),
    # Admin
    path("admin-practices/", AdminPracticesListView.as_view(), name="admin-practices"),
    # API Routers
    path("", include(student_router.urls)),
    path("", include(employer_router.urls)),
    path("", include(staff_router.urls)),
]
