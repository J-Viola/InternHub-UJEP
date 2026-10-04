from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminPracticeListView,
    CancelStudentPracticeView,
    ConfirmContractView,
    CreateInvitationView,
    DocumentReviewView,
    EmployerInvitationApprovalView,
    EmployerInvitationViewSet,
    EvaluationViewSet,
    OrganizationApplicationsView,
    ProfessorApplicationsView,
    ReapplyToPracticeView,
    ResolveCancellationView,
    StudentPracticeCardView,
    StudentPracticeContentDownloadView,
    StudentPracticeContractDownloadView,
    StudentPracticeDownloadDocumentView,
    StudentPracticeFeedbackDownloadView,
    StudentPracticeHistoryView,
    StudentPracticeListView,
    StudentPracticeReportDownloadView,
    StudentPracticeUploadDocumentView,
    TransitionStudentPracticeView,
    WithdrawStudentPracticeView,
)

app_name = "student_practices"

router = routers.DefaultRouter()
router.register(r"invitations", EmployerInvitationViewSet, basename="invitations")
router.register(r"evaluations", EvaluationViewSet, basename="evaluations")

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
    path(
        "review-document/<int:document_id>",
        DocumentReviewView.as_view(),
        name="document-review",
    ),
    # State machine endpoints
    path(
        "<int:student_practice_id>/transition/",
        TransitionStudentPracticeView.as_view(),
        name="student-practice-transition",
    ),
    path(
        "<int:student_practice_id>/withdraw/",
        WithdrawStudentPracticeView.as_view(),
        name="student-practice-withdraw",
    ),
    path(
        "<int:student_practice_id>/cancel/",
        CancelStudentPracticeView.as_view(),
        name="student-practice-cancel",
    ),
    path(
        "<int:student_practice_id>/resolve-cancellation/",
        ResolveCancellationView.as_view(),
        name="student-practice-resolve-cancellation",
    ),
    # Document generation endpoints
    path(
        "<int:student_practice_id>/contract/",
        StudentPracticeContractDownloadView.as_view(),
        name="student-practice-contract",
    ),
    path(
        "<int:student_practice_id>/content/",
        StudentPracticeContentDownloadView.as_view(),
        name="student-practice-content",
    ),
    path(
        "<int:student_practice_id>/report/",
        StudentPracticeReportDownloadView.as_view(),
        name="student-practice-report",
    ),
    path(
        "<int:student_practice_id>/feedback/",
        StudentPracticeFeedbackDownloadView.as_view(),
        name="student-practice-feedback",
    ),
    # History endpoint
    path(
        "<int:student_practice_id>/history/",
        StudentPracticeHistoryView.as_view(),
        name="student-practice-history",
    ),
    # Re-apply endpoint
    path(
        "reapply/<int:practice_id>/",
        ReapplyToPracticeView.as_view(),
        name="student-practice-reapply",
    ),
    path(
        "<int:pk>/confirm-contract/",
        ConfirmContractView.as_view(),
        name="student-practice-confirm-contract",
    ),
]
