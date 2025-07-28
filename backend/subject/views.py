from api.models import Subject, ProfessorUser, DepartmentRole
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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

    @action(detail=False, methods=['get'], url_path='department-subjects')
    def department_subjects(self, request):
        """
        Get all subjects from the department where the logged-in user is a professor.
        Only accessible by ProfessorUser with assigned department.
        """
        user = request.user
        
        # Check if user is a ProfessorUser
        if not isinstance(user, ProfessorUser):
            return Response({"error": "Přístup povolen pouze pro profesory"}, status=403)
        
        # Check if user has a department assigned
        if not user.department:
            return Response({"error": "Uživatel nemá přiřazenou katedru"}, status=400)
        
        # Get all subjects from the user's department
        subjects = Subject.objects.filter(department=user.department).select_related('department')
        
        # Serialize the subjects
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)
