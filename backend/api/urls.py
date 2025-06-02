# backend/api/urls.py

from django.urls import path, include
from rest_framework import routers

from .views import (
    StatusViewSet,
    DepartmentViewSet,
    RoleViewSet,
    SubjectViewSet,
    EmployerProfileViewSet,
    EmployerInvitationViewSet,
    EmployerUserRoleViewSet,
    PracticeTypeViewSet,
    PracticeViewSet,
    PracticeUserViewSet,
    StudentPracticeViewSet,
    UploadedDocumentViewSet,
    DepartmentUserRoleViewSet,
    UserSubjectViewSet,
)

router = routers.DefaultRouter()
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'roles', RoleViewSet, basename='role')


router.register(r'subjects', SubjectViewSet, basename='subject')

router.register(r'employers', EmployerProfileViewSet, basename='employer')
router.register(r'employer-invitations', EmployerInvitationViewSet, basename='employer-invitation')
router.register(r'employer-user-roles', EmployerUserRoleViewSet, basename='employer-user-role')

router.register(r'practice-types', PracticeTypeViewSet, basename='practicetype')
router.register(r'practices', PracticeViewSet, basename='practice')
router.register(r'practice-users', PracticeUserViewSet, basename='practiceuser')
router.register(r'student-practices', StudentPracticeViewSet, basename='studentpractice')
router.register(r'uploaded-documents', UploadedDocumentViewSet, basename='document')

router.register(r'department-user-roles', DepartmentUserRoleViewSet, basename='department-user-role')
router.register(r'user-subjects', UserSubjectViewSet, basename='user-subject')

urlpatterns = [
    path('', include(router.urls)),
]
