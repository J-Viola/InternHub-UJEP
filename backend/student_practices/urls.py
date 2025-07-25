from django.urls import path

from .views import (
    EmployerInvitationApprovalView,
    OrganizationApplicationsView,
    StudentPracticeCardView,
    StudentPracticeDownloadDocumentView,
    StudentPracticeListView,
    StudentPracticeStatusUpdateView,
    StudentPracticeUploadDocumentView,
)

app_name = "student_practices"

urlpatterns = [
    path("student-practices/by-practice/<int:practice_id>", StudentPracticeListView.as_view(), name="student-practice-list"),
    path("employer-invitation/approve/", EmployerInvitationApprovalView.as_view(), name="employer-invitation-approve"),
    path("organization-applications/", OrganizationApplicationsView.as_view(), name="organization-applications"),
    path(
        "student-practices/<int:student_practice_id>/status/",
        StudentPracticeStatusUpdateView.as_view(),
        name="student-practice-status-update",
    ),
    path(
        "student-practices/<int:student_practice_id>",
        StudentPracticeCardView.as_view(),
        name="student-practice-card",
    ),
    path("download-document/<int:document_id>", StudentPracticeDownloadDocumentView.as_view(), name="student-practice-download-document"),
    path("upload-document/<int:document_id>", StudentPracticeUploadDocumentView.as_view(), name="student-practice-upload-document"),
]
