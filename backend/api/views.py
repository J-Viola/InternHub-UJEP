from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from student_practices.models import UploadedDocument
from users.models import (
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubjectType,
)  # Importy pro nové View


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all API viewsets"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def serve_user_file(request, path):
    """
    Serve user documents with authentication and path validation.
    Supports X-Accel-Redirect for Nginx in production.
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    user = request.user
    # Build and normalize file path
    doc_root = Path(settings.STORAGE_ROOT) / "documents"
    full_path = (doc_root / path).resolve()

    # Ensure the file is inside our documents directory (security check)
    if not str(full_path).startswith(str(doc_root.resolve())):
        raise Http404("Invalid path")

    # Check file existence
    if not full_path.is_file():
        raise Http404("File not found")

    has_access = False

    if user.is_superuser:
        has_access = True
    elif "cvs/" in path:
        # Special logic for Student CVs
        filename = path.split("/")[-1]
        student = StudentUser.objects.filter(cv_file__endswith=filename).first()
        if student:
            # 1. Owner access
            if student.user_id == user.user_id:
                has_access = True
            # 2. Employer access (if student applied to their practice)
            elif isinstance(user, OrganizationUser):
                if student.student_practices.filter(practice__employer=user.employer_profile).exists():
                    has_access = True
            # 3. Professor / Dept Head access
            elif isinstance(user, ProfessorUser):
                # Check if professor teaches any subject the student is enrolled in
                if student.user_subjects.filter(
                    subject__user_subjects__user=user,
                    subject__user_subjects__role=UserSubjectType.Professor,
                ).exists():
                    has_access = True
                # Check if professor is head of department the student belongs to (via subjects)
                elif user.department_role == DepartmentRole.HEAD:
                    if student.user_subjects.filter(subject__department=user.department).exists():
                        has_access = True
    else:
        # Standard logic for practice documents
        doc = UploadedDocument.objects.filter(document__endswith=path).first()
        if doc:
            has_access = doc.user_has_permission(user)

    if not has_access:
        return HttpResponseForbidden("You do not have permission to access this document")

    # Stream the file
    return FileResponse(full_path.open("rb"))


class UniqueLocationsListView(APIView):
    @extend_schema(
        summary="Get unique practice locations",
        description="Returns a list of all unique cities/locations where practices are offered. **Permissions: Allow Any**",
        tags=["Utils"],
        responses={200: OpenApiResponse(description="List of unique locations (strings)")},
    )
    def get(self, request):
        # Získání unikátních měst z EmployerProfile
        cities = EmployerProfile.objects.exclude(city__isnull=True).exclude(city__exact="").values_list("city", flat=True)

        # Získání unikátních adres z EmployerProfile
        addresses = EmployerProfile.objects.exclude(address__isnull=True).exclude(address__exact="").values_list("address", flat=True)

        # Sjednocení a odstranění duplicit, seřazení
        all_locations = sorted(list(set(list(cities) + list(addresses))))

        return Response(all_locations, status=status.HTTP_200_OK)


class StorageAuthCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return HttpResponse(status=200)
