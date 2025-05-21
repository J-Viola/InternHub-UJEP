from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    StatusViewSet, UserViewSet, ActionLogViewSet, DepartmentViewSet,
    DepartmentUserRoleViewSet, SubjectViewSet, EmployerProfileViewSet,
    EmployerInvitationViewSet, EmployerUserRoleViewSet, PracticeTypeViewSet,
    PracticeViewSet, PracticeUserViewSet, RoleViewSet, StudentPracticeViewSet,
    UploadedDocumentViewSet, UserSubjectViewSet
)

router = DefaultRouter()
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'users', UserViewSet, basename='user')
router.register(r'action-logs', ActionLogViewSet, basename='action-log')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'department-user-roles', DepartmentUserRoleViewSet, basename='department-user-role')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'employer-profiles', EmployerProfileViewSet, basename='employer-profile')
router.register(r'employer-invitations', EmployerInvitationViewSet, basename='employer-invitation')
router.register(r'employer-user-roles', EmployerUserRoleViewSet, basename='employer-user-role')
router.register(r'practice-types', PracticeTypeViewSet, basename='practice-type')
router.register(r'practices', PracticeViewSet, basename='practice')
router.register(r'practice-users', PracticeUserViewSet, basename='practice-user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'student-practices', StudentPracticeViewSet, basename='student-practice')
router.register(r'uploaded-documents', UploadedDocumentViewSet, basename='uploaded-document')
router.register(r'user-subjects', UserSubjectViewSet, basename='user-subject')

urlpatterns = [
    path('', include(router.urls)),
]
