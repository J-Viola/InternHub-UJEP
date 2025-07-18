from django.urls import include, path
from rest_framework import routers

from .views import StudentPracticeListView, EmployerInvitationApprovalView

app_name = "student_practices"

urlpatterns = [

    path("student-practices/<int:practice_id>", StudentPracticeListView.as_view(), name="student-practice-list"),
    path("employer-invitation/approve/", EmployerInvitationApprovalView.as_view(), name="employer-invitation-approve"),
]
