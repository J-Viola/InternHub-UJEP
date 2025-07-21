from django.urls import include, path
from rest_framework import routers

from .views import StudentPracticeListView, EmployerInvitationApprovalView, OrganizationApplicationsView, StudentPracticeStatusUpdateView

app_name = "student_practices"

urlpatterns = [

    path("student-practices/<int:practice_id>", StudentPracticeListView.as_view(), name="student-practice-list"),
    path("employer-invitation/approve/", EmployerInvitationApprovalView.as_view(), name="employer-invitation-approve"),
    path("organization-applications/", OrganizationApplicationsView.as_view(), name="organization-applications"),
    path("student-practices/<int:student_practice_id>/status/", StudentPracticeStatusUpdateView.as_view(), name="student-practice-status-update"),
]
