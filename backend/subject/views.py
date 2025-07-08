from api.models import Subject
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.
from rest_framework import filters, permissions, viewsets

from .serializers import SubjectSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subjects.

    Provides CRUD operations:
    - list: GET /subjects/
    - retrieve: GET /subjects/{id}/
    - create: POST /subjects/
    - update: PUT /subjects/{id}/
    - partial update: PATCH /subjects/{id}/
    - delete: DELETE /subjects/{id}/
    """

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["department", "subject_code"]
    search_fields = ["subject_name", "subject_code"]
    ordering_fields = ["subject_name", "subject_code", "department__department_name"]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
