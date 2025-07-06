from django.urls import path

from .views import DepartmentStudentListView, DepartmentUserRoleDetailView

app_name = "department"

urlpatterns = [
    path("department-users/", DepartmentStudentListView.as_view(), name="departmentuserrole-list"),
    path("department-users/<int:pk>/", DepartmentUserRoleDetailView.as_view(), name="departmentuserrole-detail"),
]
