from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
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
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    # Build and normalize file path
    doc_root = Path(settings.STORAGE_ROOT) / "documents"
    full_path = (doc_root / path).resolve()

    # Ensure the file is inside our documents directory (security check)
    if not str(full_path).startswith(str(doc_root.resolve())):
        raise Http404("Invalid path")

    # Check file existence
    if not full_path.is_file():
        raise Http404("File not found")

    # Check permissions
    db_path = f"storage/documents/{path}"
    try:
        doc = UploadedDocument.objects.get(document=db_path)
    except UploadedDocument.DoesNotExist:
        # If not found in DB by exact path, try fallback or just 404
        # Sometimes path might be stored differently?
        raise Http404("Document record not found")

    user = request.user
    has_access = False

    if user.is_superuser:
        has_access = True
    else:
        sp = doc.student_practice
        if sp:
            if isinstance(user, StudentUser):
                if sp.user == user:
                    has_access = True

            elif isinstance(user, ProfessorUser):
                subject = sp.practice.subject
                # Check if professor is assigned to the subject
                if subject.user_subjects.filter(user=user, role=UserSubjectType.Professor).exists():
                    has_access = True
                # Check if professor is head of department
                elif user.department_role == DepartmentRole.HEAD and user.department == subject.department:
                    has_access = True

            elif isinstance(user, OrganizationUser):
                if sp.practice.employer == user.employer_profile:
                    has_access = True

    if not has_access:
        return HttpResponseForbidden("You do not have permission to access this document")

    # Stream the file
    return FileResponse(full_path.open("rb"))


class UniqueLocationsListView(APIView):
    """
    API View to retrieve a list of unique cities and addresses from EmployerProfiles.
    """

    permission_classes = [permissions.AllowAny]  # Povolit prozatím komukoliv

    def get(self, request, *args, **kwargs):
        # Získání unikátních měst z EmployerProfile
        cities = EmployerProfile.objects.exclude(city__isnull=True).exclude(city__exact="").values_list("city", flat=True)

        # Získání unikátních adres z EmployerProfile
        addresses = EmployerProfile.objects.exclude(address__isnull=True).exclude(address__exact="").values_list("address", flat=True)

        # Sjednocení a odstranění duplicit, seřazení
        all_locations = sorted(list(set(list(cities) + list(addresses))))

        return Response(all_locations, status=status.HTTP_200_OK)
