# backend/api/views.py

from datetime import date
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser

from .models import (
    Status,
    User,
    ActionLog,
    Department,
    DepartmentUserRole,
    Subject,
    EmployerProfile,
    EmployerInvitation,
    EmployerUserRole,
    PracticeType,
    Practice,
    PracticeUser,
    Role,
    StudentPractice,
    UploadedDocument,
    UserSubject
)
from .serializers import (
    StatusSerializer,
    UserSerializer,
    ActionLogSerializer,
    DepartmentSerializer,
    DepartmentUserRoleSerializer,
    SubjectSerializer,
    EmployerProfileSerializer,
    EmployerInvitationSerializer,
    EmployerUserRoleSerializer,
    PracticeTypeSerializer,
    PracticeSerializer,
    PracticeUserSerializer,
    RoleSerializer,
    StudentPracticeSerializer,
    UploadedDocumentSerializer,
    UserSubjectSerializer
)

# -------------------------------------------------------------
# Nastavení vlastní stránkovací třídy pro všechny viewsety
# -------------------------------------------------------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


#Role: Student, Vedení organizace, Správce společnosti, Správce inzerátů, Správce předmětů, Správce katedry
# Generally by smazané věci měli být schováné a přístup by měl mít pouze superadmin nebo vedení katedry, ostatní uživatelé by měli vidět pouze aktivní záznamy (deleted_at=xxxxx),
# to znamená defaultně filtrovat v list a retrieve metodách nesmazané záznamy (deleted_at=None)

# -------------------------------------------------------------
# StatusViewSet – CRUD pro statusy
# -------------------------------------------------------------
class StatusViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/statuses/
    - GET (list): Vrací seznam všech statusů (volný přístup)
    - POST: Vytvoří nový status (autentizace požadována) - Superadmin
    - GET /{id}/: Vrací detail konkrétního statusu (volný přístup)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje existující status (autentizace požadována) - Superadmin
    - DELETE /{id}/: Smaže status (autentizace požadována) - Superadmin
    """
    queryset = Status.objects.all().order_by('status_name')
    serializer_class = StatusSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['status_name']
    ordering_fields = ['status_name', 'status_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/statuses/
        statuses = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(statuses)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/statuses/{id}/
        status_obj = self.get_object()
        serializer = self.get_serializer(status_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/statuses/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/statuses/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/statuses/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/statuses/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def active(self, request):
        """
        GET /api/statuses/active/
        Vrací seznam pouze aktivních statusů (př. is_active=True)
        """
        active_statuses = Status.objects.filter(is_active=True).order_by('status_name')
        serializer = self.get_serializer(active_statuses, many=True)
        return Response(serializer.data)

#Superadmin
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def deactivate(self, request, pk=None):
        """
        POST /api/statuses/{id}/deactivate/
        Nastaví daný status jako neaktivní (is_active=False)
        """
        status_obj = self.get_object()
        status_obj.is_active = False
        status_obj.save()
        serializer = self.get_serializer(status_obj)
        return Response(serializer.data)


# -------------------------------------------------------------
# UserViewSet – CRUD a registrace uživatelů
# -------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/users/
    - GET (list): Vrací seznam všech uživatelů - superadmin, vedení katedry, správci společnosti a správci inzerátů (filtrovaný podle předmětů a pouze studenti možná udělat samostatný endpoint)
    - POST: Registrace nového uživatele - superadmin, vedení katedry (bude tam minimálně proces vytváření nebude to pouze CRUD)
    - GET /{id}/: Vrací detail uživatele - superadmin, vedení katedry, správci společnosti a správci inzerátů
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje uživatele - superadmin a uživatel sám sebe (bude krapet složitější)
    - DELETE /{id}/: Smaže uživatele - superadmin, vedení katedry, uživatel sám sebe
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined', 'last_name']

    def get_permissions(self):
        # list, retrieve a create jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/users/
        users = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/users/{id}/
        user_obj = self.get_object()
        serializer = self.get_serializer(user_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/users/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/users/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/users/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/users/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def deactivate(self, request, pk=None):
        """
        POST /api/users/{id}/deactivate/
        Deaktivuje uživatele (is_active=False)
        """
        user_obj = self.get_object()
        user_obj.is_active = False
        user_obj.save()
        serializer = self.get_serializer(user_obj)
        return Response(serializer.data)

#Všichni kromě studenta a školy
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reset_password(self, request, pk=None):
        """
        POST /api/users/{id}/reset_password/
        Umožní administrátorovi vygenerovat náhodné heslo a poslat uživatelovi (vrací nové heslo v odpovědi)
        """
        user_obj = self.get_object()
        new_password = User.objects.make_random_password()
        user_obj.set_password(new_password)
        user_obj.save()
        return Response({'new_password': new_password}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        GET /api/users/me/
        Vrací informace o aktuálně přihlášeném uživateli
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# -------------------------------------------------------------
# ActionLogViewSet – CRUD pro záznamy akcí (logy)
# -------------------------------------------------------------
class ActionLogViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/actionlogs/
    - GET (list): Vrací seznam všech záznamů akcí - superadmin, vedení katedry
    - POST: Vytvoří nový záznam akce - SMAZAT
    - GET /{id}/: Vrací detail záznamu akce - superadmin, vedení katedry
    - PUT /{id}/ nebo PATCH /{id}/: SMAZAT
    - DELETE /{id}/: Smaže záznam akce - SMAZAT
    """
    queryset = ActionLog.objects.all().order_by('-action_date')
    serializer_class = ActionLogSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action_type', 'description', 'user__username']
    ordering_fields = ['timestamp', 'action_type']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/actionlogs/
        logs = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/actionlogs/{id}/
        log_obj = self.get_object()
        serializer = self.get_serializer(log_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/actionlogs/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/actionlogs/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/actionlogs/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/actionlogs/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

#superadmin, vedení katedry
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def recent(self, request):
        """
        GET /api/actionlogs/recent/
        Vrací posledních 10 záznamů logu
        """
        recent_logs = ActionLog.objects.all().order_by('-timestamp')[:10]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# DepartmentViewSet – CRUD pro oddělení
# -------------------------------------------------------------
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/departments/
    - GET (list): Vrací seznam oddělení - superadmin, vedení katedry
    - POST: Vytvoří nové oddělení - superadmin
    - GET /{id}/: Vrací detail oddělení - superadmin, vedení katedry
    - PUT /{id}/ nebo PATCH /{id}/: - superadmin, vedení katedry (sám sobě)
    - DELETE /{id}/: Smaže oddělení - superadmin
    """
    queryset = Department.objects.all().order_by('department_name')
    serializer_class = DepartmentSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['department_name']
    ordering_fields = ['department_name', 'department_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/departments/
        departments = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(departments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/departments/{id}/
        dept_obj = self.get_object()
        serializer = self.get_serializer(dept_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/departments/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/departments/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/departments/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/departments/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

#superadmin, vedení katedry
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def with_users(self, request):
        """
        GET /api/departments/with_users/
        Vrací oddělení včetně přiřazených uživatelů (nested)
        """
        departments = Department.objects.prefetch_related('departmentuserrole_set').all()
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# DepartmentUserRoleViewSet – CRUD pro role uživatelů v odděleních
# -------------------------------------------------------------
class DepartmentUserRoleViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/departmentuserroles/
    - GET (list): Vrací všechny role uživatelů v odděleních - superadmin, vedení katedry
    - POST: Přiřadí uživatele k oddělení s rolí - superadmin,
    - GET /{id}/: Vrací detail přiřazení - vedení katedry
    - PUT /{id}/ nebo PATCH /{id}/: - superadmin,
    - DELETE /{id}/: Odebere uživatele z oddělení - superadmin,
    """
    queryset = DepartmentUserRole.objects.all().order_by('id')
    serializer_class = DepartmentUserRoleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['department__department_name', 'user__username', 'role__role_name']
    ordering_fields = ['id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/departmentuserroles/
        roles = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(roles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/departmentuserroles/{id}/
        role_obj = self.get_object()
        serializer = self.get_serializer(role_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/departmentuserroles/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/departmentuserroles/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/departmentuserroles/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/departmentuserroles/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# superadmin, vedení katedry
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_department(self, request):
        """
        GET /api/departmentuserroles/by_department/?department_id={id}
        Vrací přiřazení uživatelů pro dané oddělení
        """
        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response({'detail': 'Chybí department_id'}, status=status.HTTP_400_BAD_REQUEST)
        roles = DepartmentUserRole.objects.filter(department_id=dept_id).select_related('user', 'role')
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# RoleViewSet – CRUD pro role
# -------------------------------------------------------------
class RoleViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/roles/
    - GET (list): Vrací seznam rolí (autentizace požadována)
    - POST: Vytvoří novou roli - superadmin
    - GET /{id}/: Vrací detail role (autentizace požadována)
    - PUT /{id}/ nebo PATCH /{id}/: - superadmin
    - DELETE /{id}/: Smaže roli - superadmin
    """
    queryset = Role.objects.all().order_by('role_name')
    serializer_class = RoleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['role_name']
    ordering_fields = ['role_name', 'role_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/roles/
        roles = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(roles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/roles/{id}/
        role_obj = self.get_object()
        serializer = self.get_serializer(role_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/roles/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/roles/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/roles/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/roles/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def choices(self, request):
        """
        GET /api/roles/choices/
        Vrací pouze id a název rolí pro dropdown
        """
        roles = Role.objects.all().order_by('role_name')
        data = [{'role_id': r.role_id, 'role_name': r.role_name} for r in roles]
        return Response(data)


# -------------------------------------------------------------
# SubjectViewSet – CRUD a filtrování předmětů
# -------------------------------------------------------------
class SubjectViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/subjects/
    - GET (list): Vrací seznam všech předmětů (autentizace požadována)
    - POST: Vytvoří nový předmět - superadmin, vedení katedry
    - GET /{id}/: Vrací detail předmětu (autentizace požadována)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje předmět  - superadmin, vedení katedry
    - DELETE /{id}/: Smaže předmět  - superadmin, vedení katedry
    """
    queryset = Subject.objects.all().order_by('subject_name')
    serializer_class = SubjectSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject_name', 'subject_code', 'department__department_name']
    ordering_fields = ['subject_name', 'subject_code', 'subject_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/subjects/
        subjects = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(subjects)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/subjects/{id}/
        subj = self.get_object()
        serializer = self.get_serializer(subj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/subjects/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/subjects/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/subjects/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/subjects/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_department(self, request):
        """
        GET /api/subjects/by_department/?department_id={id}
        Vrací předměty patřící do konkrétního oddělení
        """
        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response({'detail': 'Chybí department_id'}, status=status.HTTP_400_BAD_REQUEST)
        subjects = Subject.objects.filter(department_id=dept_id).order_by('subject_name')
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# EmployerProfileViewSet – CRUD a vyhledávání zaměstnavatelů
# -------------------------------------------------------------
class EmployerProfileViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/employers/
    - GET (list): Vrací seznam zaměstnavatelů - (autentizace požadována)
    - POST: Vytvoří profil zaměstnavatele - organizace, superadmin, vedení katedry (složitější proces registrace)
    - GET /{id}/: Vrací detail profilu - (autentizace požadována)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje profil - organizace, superadmin, vedení katedry
    - DELETE /{id}/: Smaže profil - organizace, superadmin
    """
    queryset = EmployerProfile.objects.all().order_by('company_name')
    serializer_class = EmployerProfileSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['company_name', 'ico', 'address']
    ordering_fields = ['company_name', 'employer_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/employers/
        employers = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(employers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(employers, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/employers/{id}/
        emp = self.get_object()
        serializer = self.get_serializer(emp)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/employers/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/employers/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/employers/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/employers/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# superadmin, vedení katedry, správce předmětů
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def approved(self, request):
        """
        GET /api/employers/approved/
        Vrací pouze schválené zaměstnavatele (approval_status= schváleno)
        """
        approved_status = Status.objects.filter(status_name__icontains='approved').first()
        if not approved_status:
            return Response([], status=status.HTTP_200_OK)
        employers = EmployerProfile.objects.filter(approval_status=approved_status).order_by('company_name')
        serializer = self.get_serializer(employers, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# EmployerInvitationViewSet – CRUD pozvánek zaměstnavatele
# -------------------------------------------------------------
class EmployerInvitationViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/employer-invitations/
    - GET (list): Vrací seznam pozvánek - superadmin, vedení katedry, správci společnosti, správci inzerátů, správce předmětů
    - POST: Vytvoří novou pozvánku - superadmin, vedení katedry, správci společnosti, správci inzerátů
    - GET /{id}/: Vrací detail pozvánky - superadmin, vedení katedry, správci společnosti, správci inzerátů
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje pozvánku - superadmin, vedení katedry, správci společnosti, správci inzerátů
    - DELETE /{id}/: Smaže pozvánku - superadmin, vedení katedry, správci společnosti, správci inzerátů
    """
    queryset = EmployerInvitation.objects.all().order_by('-submission_date')
    serializer_class = EmployerInvitationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'practice__title', 'status__status_name']
    ordering_fields = ['invitation_id', 'sent_at', 'expiration_date']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/employer-invitations/
        invites = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(invites)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(invites, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/employer-invitations/{id}/
        invite = self.get_object()
        serializer = self.get_serializer(invite)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/employer-invitations/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/employer-invitations/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/employer-invitations/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/employer-invitations/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

#superadmin, vedení katedry, správci společnosti, správci inzerátů
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def pending(self, request):
        """
        GET /api/employer-invitations/pending/
        Vrací pouze nevyřízené pozvánky (status pending)
        """
        pending_status = Status.objects.filter(status_name__icontains='pending').first()
        if not pending_status:
            return Response([], status=status.HTTP_200_OK)
        invites = EmployerInvitation.objects.filter(status=pending_status).order_by('-sent_at')
        serializer = self.get_serializer(invites, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# EmployerUserRoleViewSet – CRUD role uživatelů u zaměstnavatelů
# -------------------------------------------------------------
class EmployerUserRoleViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/employer-user-roles/
    - GET (list): Vrací seznam rolí uživatelů u zaměstnavatelů - superadmin, vedení katedry, správci společnosti, správci inzerátů (společnost uvidí sama sebe)
    - POST: Přiřadí uživatele k zaměstnavateli s rolí - superadmin, vedení katedry (společnost pozve zaměstnance)
    - GET /{id}/: Vrací detail přiřazení - superadmin, vedení katedry, správci společnosti, správci inzerátů (společnost uvidí sama sebe)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje přiřazení - superadmin, vedení katedry, správci společnosti (společnost upravuje sama sebe)
    - DELETE /{id}/: Odebere uživatele od zaměstnavatele - superadmin, vedení katedry, správci společnosti (společnost upravuje sama sebe)
    """
    queryset = EmployerUserRole.objects.all().order_by('id')
    serializer_class = EmployerUserRoleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['employer__company_name', 'user__username']
    ordering_fields = ['id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/employer-user-roles/
        roles = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(roles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/employer-user-roles/{id}/
        role = self.get_object()
        serializer = self.get_serializer(role)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/employer-user-roles/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/employer-user-roles/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/employer-user-roles/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/employer-user-roles/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_employer(self, request):
        """
        GET /api/employer-user-roles/by_employer/?employer_id={id}
        Vrací přiřazení uživatelů pro daného zaměstnavatele
        """
        emp_id = request.query_params.get('employer_id')
        if not emp_id:
            return Response({'detail': 'Chybí employer_id'}, status=status.HTTP_400_BAD_REQUEST)
        roles = EmployerUserRole.objects.filter(employer_id=emp_id).select_related('user')
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# PracticeTypeViewSet – CRUD typů praxí
# -------------------------------------------------------------
class PracticeTypeViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/practice-types/
    - GET (list): Vrací seznam typů praxí (autentizace požadována)
    - POST: Vytvoří nový typ praxe - superadmin, vedení katedry
    - GET /{id}/: Vrací detail typu praxe (autentizace požadována)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje typ praxe - superadmin, vedení katedry
    - DELETE /{id}/: Smaže typ praxe (autentizace požadována)
    """
    queryset = PracticeType.objects.all().order_by('name')
    serializer_class = PracticeTypeSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'practice_type_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/practice-types/
        types = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(types)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(types, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/practice-types/{id}/
        pt = self.get_object()
        serializer = self.get_serializer(pt)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/practice-types/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practice-types/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/practice-types/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practice-types/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def choices(self, request):
        """
        GET /api/practice-types/choices/
        Vrací pouze id a název typů praxí pro dropdown
        """
        types = PracticeType.objects.all().order_by('type_name')
        data = [{'practice_type_id': t.practice_type_id, 'type_name': t.type_name} for t in types]
        return Response(data)


# -------------------------------------------------------------
# PracticeViewSet – CRUD a správa praxí, včetně přihlášení
# -------------------------------------------------------------
class PracticeViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/practices/
    - GET (list): Vrací veřejný seznam aktivních praxí - superadmin, správce katedry, správce inzerátů, správce společnosti, student
    - POST: Vytvoří novou praxi - superadmin, správce katedry, správce inzerátů, správce společnosti
    - GET /{id}/: Vrací detail praxe - superadmin, správce katedry, správce inzerátů, správce předmětů, správce společnosti, student
    - PUT /{id}/ nebo PATCH /{id}/: - superadmin, správce katedry, správce inzerátů, správce předmětů, správce společnosti, student
    - DELETE /{id}/: Smaže praxi - superadmin, správce katedry,
    - POST /{id}/apply/: Student se hlásí na praxi (autentizace požadována)
    xxx
    """
    queryset = Practice.objects.all().select_related("employer", "practice_type", "status", "approval_status")
    serializer_class = PracticeSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'employer__company_name']
    ordering_fields = ['start_date', 'end_date', 'title', 'practice_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/practices/
        practices = self.filter_queryset(self.queryset.filter(is_active=True))
        page = self.paginate_queryset(practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/practices/{id}/
        practice_obj = self.get_object()
        serializer = self.get_serializer(practice_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/practices/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practices/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/practices/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practices/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def apply(self, request, pk=None):
        # POST /api/practices/{id}/apply/
        practice_obj = self.get_object()
        data = request.data  # Data z frontendu (např. user_id, cover_letter apod.)
        # Vytvoření záznamu StudentPractice s logikou: pokud už je student přihlášen, vrací chybu
        existing = StudentPractice.objects.filter(practice=practice_obj, user=request.user).first()
        if existing:
            return Response({'detail': 'Již jste přihlášen(a) na tuto praxi.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StudentPracticeSerializer(data={'practice': practice_obj.id, **data})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def upcoming(self, request):
        """
        GET /api/practices/upcoming/
        Vrací praxe, které budou začínat v budoucnu (start_date >= dnes)
        """
        today = date.today()
        upcoming_practices = Practice.objects.filter(start_date__gte=today, is_active=True).order_by('start_date')
        page = self.paginate_queryset(upcoming_practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(upcoming_practices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_subject(self, request):
        """
        GET /api/practices/by_subject/?subject_id={id}
        Vrací praxe patřící k danému předmětu
        """
        subj_id = request.query_params.get('subject_id')
        if not subj_id:
            return Response({'detail': 'Chybí subject_id'}, status=status.HTTP_400_BAD_REQUEST)
        practices = Practice.objects.filter(subject_id=subj_id, is_active=True).order_by('start_date')
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# PracticeUserViewSet – CRUD přiřazení uživatelů k praxím
# -------------------------------------------------------------
class PracticeUserViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/practice-users/
    - GET (list): Vrací seznam všech přiřazení uživatelů k praxím (volný přístup)
    - POST: Přiřadí uživatele k praxi (autentizace požadována)
    - GET /{id}/: Vrací detail přiřazení (volný přístup)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje přiřazení (autentizace požadována)
    - DELETE /{id}/: Odebere uživatele z praxe (autentizace požadována)
    """
    queryset = PracticeUser.objects.all().order_by('id')
    serializer_class = PracticeUserSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['practice__title', 'user__username']
    ordering_fields = ['id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/practice-users/
        pus = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(pus)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(pus, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/practice-users/{id}/
        pu = self.get_object()
        serializer = self.get_serializer(pu)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/practice-users/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practice-users/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/practice-users/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practice-users/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------------------------------------------------
# StudentPracticeViewSet – CRUD přihlášek studenta, pouze pro vlastního uživatele
# -------------------------------------------------------------
class StudentPracticeViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/student-practices/
    - GET (list): Vrací seznam přihlášek studenta k praxím (pouze autentizovaný uživatel)
    - POST: Vytvoří novou přihlášku (autentizace požadována; student se hlásí přes PracticeViewSet.apply)
    - GET /{id}/: Vrací detail přihlášky (pouze autentizovaný uživatel vlastní data)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje přihlášku (autentizace požadována)
    - DELETE /{id}/: Smaže přihlášku (autentizace požadována)
    """
    serializer_class = StudentPracticeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Vrací pouze přihlášky přihlášeného uživatele
        return StudentPractice.objects.filter(user=self.request.user).select_related(
            "practice", "approval_status", "progress_status"
        ).order_by('-application_date')

    def list(self, request, *args, **kwargs):
        # GET /api/student-practices/
        student_practices = self.get_queryset()
        page = self.paginate_queryset(student_practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(student_practices, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/student-practices/{id}/
        sp = self.get_object()
        # Zajištění, že uživatel může vidět pouze své vlastní přihlášky
        if sp.user != request.user:
            return Response({'detail': 'Nemáte přístup k této přihlášce.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(sp)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/student-practices/
        data = request.data  # Data z frontendu
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/student-practices/{id}/
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'detail': 'Nemáte oprávnění upravovat tuto přihlášku.'}, status=status.HTTP_403_FORBIDDEN)
        partial = kwargs.pop('partial', False)
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/student-practices/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/student-practices/{id}/
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'detail': 'Nemáte oprávnění odstranit tuto přihlášku.'}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        POST /api/student-practices/{id}/cancel/
        Stornuje přihlášku studenta s uvedením důvodu v request.data['cancellation_reason']
        """
        sp = self.get_object()
        if sp.user != request.user:
            return Response({'detail': 'Nemáte oprávnění stornovat tuto přihlášku.'}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get('cancellation_reason', '')
        sp.cancellation_reason = reason
        sp.cancelled_by_user = request.user
        sp.progress_status = Status.objects.filter(status_name__icontains='cancelled').first()
        sp.save()
        serializer = self.get_serializer(sp)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def stats(self, request):
        """
        GET /api/student-practices/stats/
        Vrací statistiky (počet přihlášek, dokončených hodin, atd.) pro přihlášeného uživatele
        """
        total = self.get_queryset().count()
        completed_hours = sum([sp.hours_completed for sp in self.get_queryset()])
        return Response({
            'total_applications': total,
            'total_completed_hours': completed_hours
        })


# -------------------------------------------------------------
# UploadedDocumentViewSet – CRUD nahraných dokumentů (souborů)
# -------------------------------------------------------------
class UploadedDocumentViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/uploaded-documents/
    - GET (list): Vrací seznam nahraných dokumentů (volný přístup)
    - POST: Nahraje nový dokument (autentizace požadována)
    - GET /{id}/: Vrací detail dokumentu (volný přístup)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje dokument (autentizace požadována)
    - DELETE /{id}/: Smaže dokument (autentizace požadována)
    """
    queryset = UploadedDocument.objects.all().order_by('-uploaded_at')
    serializer_class = UploadedDocumentSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['document_name', 'practice__title']
    ordering_fields = ['uploaded_at', 'document_id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/uploaded-documents/
        docs = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(docs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/uploaded-documents/{id}/
        doc = self.get_object()
        serializer = self.get_serializer(doc)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/uploaded-documents/
        data = request.data  # Data z frontendu (včetně souboru)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/uploaded-documents/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/uploaded-documents/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/uploaded-documents/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_practice(self, request):
        """
        GET /api/uploaded-documents/by_practice/?practice_id={id}
        Vrací dokumenty patřící k dané praxi
        """
        practice_id = request.query_params.get('practice_id')
        if not practice_id:
            return Response({'detail': 'Chybí practice_id'}, status=status.HTTP_400_BAD_REQUEST)
        docs = UploadedDocument.objects.filter(practice_id=practice_id).order_by('-uploaded_at')
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)


# -------------------------------------------------------------
# UserSubjectViewSet – CRUD přiřazení uživatelů k předmětům
# -------------------------------------------------------------
class UserSubjectViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/user-subjects/
    - GET (list): Vrací seznam všech přiřazení uživatelů k předmětům (volný přístup)
    - POST: Vytvoří nové přiřazení (autentizace požadována)
    - GET /{id}/: Vrací detail přiřazení (volný přístup)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje přiřazení (autentizace požadována)
    - DELETE /{id}/: Smaže přiřazení (autentizace požadována)
    """
    queryset = UserSubject.objects.all().order_by('id')
    serializer_class = UserSubjectSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'subject__subject_name']
    ordering_fields = ['id']

    def get_permissions(self):
        # list a retrieve jsou veřejné; ostatní akce vyžadují autentizaci
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        # GET /api/user-subjects/
        us = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(us)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(us, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # GET /api/user-subjects/{id}/
        us_obj = self.get_object()
        serializer = self.get_serializer(us_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # POST /api/user-subjects/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/user-subjects/{id}/
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/user-subjects/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/user-subjects/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
