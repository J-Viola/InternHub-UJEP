from rest_framework import viewsets
from .models import (
    Status, User, ActionLog, Department, DepartmentUserRole, Subject,
    EmployerProfile, EmployerInvitation, EmployerUserRole, PracticeType,
    Practice, PracticeUser, Role, StudentPractice, UploadedDocument, UserSubject
)
from .serializers import (
    StatusSerializer, UserSerializer, ActionLogSerializer, DepartmentSerializer,
    DepartmentUserRoleSerializer, SubjectSerializer, EmployerProfileSerializer,
    EmployerInvitationSerializer, EmployerUserRoleSerializer, PracticeTypeSerializer,
    PracticeSerializer, PracticeUserSerializer, RoleSerializer, StudentPracticeSerializer,
    UploadedDocumentSerializer, UserSubjectSerializer
)

class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class ActionLogViewSet(viewsets.ModelViewSet):
    queryset = ActionLog.objects.all()
    serializer_class = ActionLogSerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class DepartmentUserRoleViewSet(viewsets.ModelViewSet):
    queryset = DepartmentUserRole.objects.all()
    serializer_class = DepartmentUserRoleSerializer

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class EmployerProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployerProfile.objects.all()
    serializer_class = EmployerProfileSerializer

class EmployerInvitationViewSet(viewsets.ModelViewSet):
    queryset = EmployerInvitation.objects.all()
    serializer_class = EmployerInvitationSerializer

class EmployerUserRoleViewSet(viewsets.ModelViewSet):
    queryset = EmployerUserRole.objects.all()
    serializer_class = EmployerUserRoleSerializer

class PracticeTypeViewSet(viewsets.ModelViewSet):
    queryset = PracticeType.objects.all()
    serializer_class = PracticeTypeSerializer

class PracticeViewSet(viewsets.ModelViewSet):
    queryset = Practice.objects.all()
    serializer_class = PracticeSerializer

class PracticeUserViewSet(viewsets.ModelViewSet):
    queryset = PracticeUser.objects.all()
    serializer_class = PracticeUserSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class StudentPracticeViewSet(viewsets.ModelViewSet):
    queryset = StudentPractice.objects.all()
    serializer_class = StudentPracticeSerializer

class UploadedDocumentViewSet(viewsets.ModelViewSet):
    queryset = UploadedDocument.objects.all()
    serializer_class = UploadedDocumentSerializer

class UserSubjectViewSet(viewsets.ModelViewSet):
    queryset = UserSubject.objects.all()
    serializer_class = UserSubjectSerializer
