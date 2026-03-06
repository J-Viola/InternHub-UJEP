from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminPracticeListView,
    CreateInvitationView,
    EmployerInvitationApprovalView,
    EmployerInvitationViewSet,
    OrganizationApplicationsView,
    ProfessorApplicationsView,
    StudentPracticeCardView,
    StudentPracticeDownloadDocumentView,
    StudentPracticeListView,
    StudentPracticeStatusUpdateView,
    StudentPracticeUploadDocumentView,
)

app_name = "student_practices"

router = routers.DefaultRouter()
router.register(r"invitations", EmployerInvitationViewSet, basename="invitations")

urlpatterns = [
    path("", include(router.urls)),
    # Admin
    path(
        "admin-view/pending-practices/",
        AdminPracticeListView.as_view(),
        name="admin-practice-list",
    ),
    path(
        "professor-applications/",
        ProfessorApplicationsView.as_view(),
        name="professor-applications",
    ),
    # Zbytek API
    path(
        "by-practice/<int:practice_id>",
        StudentPracticeListView.as_view(),
        name="student-practice-list",
    ),
    path(
        "employer-invitation/create/",
        CreateInvitationView.as_view(),
        name="employer-invitation-create",
    ),
    path(
        "employer-invitation/approve/",
        EmployerInvitationApprovalView.as_view(),
        name="employer-invitation-approve",
    ),
    path(
        "organization-applications/",
        OrganizationApplicationsView.as_view(),
        name="organization-applications",
    ),
    path(
        "<int:student_practice_id>/status/",
        StudentPracticeStatusUpdateView.as_view(),
        name="student-practice-status-update",
    ),
    path(
        "<int:student_practice_id>",
        StudentPracticeCardView.as_view(),
        name="student-practice-card",
    ),
    path(
        "download-document/<int:document_id>",
        StudentPracticeDownloadDocumentView.as_view(),
        name="student-practice-download-document",
    ),
    path(
        "upload-document/<int:document_id>",
        StudentPracticeUploadDocumentView.as_view(),
        name="student-practice-upload-document",
    ),
]
