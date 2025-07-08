from datetime import date

from api.decorators import role_required
from api.models import Practice, StudentPractice
from api.serializers import PracticeSerializer, StudentPracticeSerializer
from api.views import StandardResultsSetPagination
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from users.models import OrganizationRoleEnum, StagRoleEnum


# -------------------------------------------------------------
# PracticeViewSet – CRUD a správa praxí, včetně přihlášení
# -------------------------------------------------------------
class PracticeViewSet(viewsets.ModelViewSet):
    """
    Endpoint: /api/practices/
    - GET (list): Vrací veřejný seznam aktivních praxí (volný přístup)
    - POST: Vytvoří novou praxi (autentizace požadována)
    - GET /{id}/: Vrací detail praxe (volný přístup)
    - PUT /{id}/ nebo PATCH /{id}/: Aktualizuje praxi (autentizace požadována)
    - DELETE /{id}/: Smaže praxi (autentizace požadována)
    - POST /{id}/apply/: Student se hlásí na praxi (autentizace požadována)
    """

    queryset = Practice.objects.all().select_related("employer", "practice_type")
    serializer_class = PracticeSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "employer__company_name"]
    ordering_fields = ["start_date", "end_date", "title", "practice_id"]

    def get_permissions(self):
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

    @role_required([OrganizationRoleEnum.INSERT, OrganizationRoleEnum.OWNER, StagRoleEnum.VY])
    def create(self, request, *args, **kwargs):
        # POST /api/practices/
        data = request.data  # Data z frontendu
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @role_required([OrganizationRoleEnum.OWNER, OrganizationRoleEnum.INSERT, StagRoleEnum.VY])
    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practices/{id}/
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @role_required([OrganizationRoleEnum.OWNER, OrganizationRoleEnum.INSERT, StagRoleEnum.VY])
    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/practices/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    @role_required([OrganizationRoleEnum.OWNER, OrganizationRoleEnum.INSERT, StagRoleEnum.VY])
    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practices/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def apply(self, request, pk=None):
        # POST /api/practices/{id}/apply/
        practice_obj = self.get_object()
        data = request.data  # Data z frontendu (např. user_id, cover_letter apod.)
        # Vytvoření záznamu StudentPractice s logikou: pokud už je student přihlášen, vrací chybu
        existing = StudentPractice.objects.filter(practice=practice_obj, user=request.user).first()
        if existing:
            return Response({"detail": "Již jste přihlášen(a) na tuto praxi."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StudentPracticeSerializer(data={"practice": practice_obj.id, **data})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def upcoming(self, request):
        """
        GET /api/practices/upcoming/
        Vrací praxe, které budou začínat v budoucnu (start_date >= dnes)
        """
        today = date.today()
        upcoming_practices = Practice.objects.filter(start_date__gte=today, is_active=True).order_by("start_date")
        page = self.paginate_queryset(upcoming_practices)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(upcoming_practices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def by_subject(self, request):
        """
        GET /api/practices/by_subject/?subject_id={id}
        Vrací praxe patřící k danému předmětu
        """
        subj_id = request.query_params.get("subject_id")
        if not subj_id:
            return Response({"detail": "Chybí subject_id"}, status=status.HTTP_400_BAD_REQUEST)
        practices = Practice.objects.filter(subject_id=subj_id, is_active=True).order_by("start_date")
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)
