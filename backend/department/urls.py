from django.urls import path

from .views import DepartmentProfessorListView, DepartmentStudentListView, DepartmentUserRoleDetailView

app_name = "department"

urlpatterns = [
    path("department-students/", DepartmentStudentListView.as_view(), name="departmentuserrole-list"),
    path("department-users/<int:pk>/", DepartmentUserRoleDetailView.as_view(), name="departmentuserrole-detail"),
    path("department-professor/", DepartmentProfessorListView.as_view(), name="departmentprofessor-list"),
]
