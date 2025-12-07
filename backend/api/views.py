from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import EmployerProfile  # Importy pro nové View


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all API viewsets"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def serve_user_file(request, path):
    """
    Serve user documents with authentication and path validation.

    TODO: Implement granular permissions (students see their own documents,
    subject teachers and department heads see related documents)
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
