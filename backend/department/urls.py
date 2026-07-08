from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminDepartmentViewSet,
    AllDepartmentProfessorListView,
    DepartmentProfessorDetailView,
    DepartmentProfessorListView,
    DepartmentStudentListView,
)

app_name = "department"
router = routers.DefaultRouter()
router.register(r"admin-departments", AdminDepartmentViewSet, basename="admin-department")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "department-users/",
        DepartmentStudentListView.as_view(),
        name="departmentuserrole-list",
    ),
    path(
        "department-students/",
        DepartmentStudentListView.as_view(),
        name="departmentuserrole-list",
    ),
    path(
        "department-professor/",
        DepartmentProfessorListView.as_view(),
        name="departmentprofessor-list",
    ),
    path(
        "department-professor/all/",
        AllDepartmentProfessorListView.as_view(),
        name="departmentprofessor-all",
    ),
    path(
        "department-professor/<int:pk>/",
        DepartmentProfessorDetailView.as_view(),
        name="departmentprofessor-detail",
    ),
]
