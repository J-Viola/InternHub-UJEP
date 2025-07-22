from django.urls import include, path
from rest_framework import routers

from .views import AdminDepartmentViewSet, DepartmentProfessorListView, DepartmentStudentListView, DepartmentUserRoleDetailView

app_name = "department"
router = routers.DefaultRouter()
router.register(r"admin-departments", AdminDepartmentViewSet, basename="practice")

urlpatterns = [
    path("", include(router.urls)),
    path("department-users/", DepartmentStudentListView.as_view(), name="departmentuserrole-list"),
    path("department-students/", DepartmentStudentListView.as_view(), name="departmentuserrole-list"),
    path("department-users/<int:pk>/", DepartmentUserRoleDetailView.as_view(), name="departmentuserrole-detail"),
    path("department-professor/", DepartmentProfessorListView.as_view(), name="departmentprofessor-list"),
]
