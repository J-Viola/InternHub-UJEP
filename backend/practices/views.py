from datetime import date
from datetime import datetime

from api.decorators import role_required
from api.models import Department, OrganizationRole, Practice, StudentPractice, StudentUser
from api.serializers import PracticeSerializer
from practices.serializers import StudentPracticeSerializer
from api.views import StandardResultsSetPagination
from practices.serializers import RunningPracticeSerializer
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import StagRoleEnum
from api.models import ApprovalStatus, ProgressStatus, SemesterType, EmployerInvitation

# -------------------------------------------------------------
# PracticeViewSet – CRUD a správa praxí, včetně přihlášení
# -------------------------------------------------------------
class PracticeViewSet(viewsets.ModelViewSet):

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

    @role_required([OrganizationRole.INSERTER, OrganizationRole.OWNER, StagRoleEnum.VY])
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        # Fix date format for start_date and end_date
        for date_field in ["start_date", "end_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    if "." in data[date_field]:
                        parsed = datetime.strptime(data[date_field], "%d.%m.%Y")
                        data[date_field] = parsed.strftime("%Y-%m-%d")
                except Exception:
                    pass

        # Nastav employer_id podle přihlášeného uživatele, pokud není v datech
        if not data.get('employer_id') and hasattr(user, 'employer_profile') and user.employer_profile:
            data['employer_id'] = user.employer_profile.employer_id
            # Nastav logo z employer profilu
            if user.employer_profile.logo:
                import base64
                import mimetypes
                if hasattr(user.employer_profile.logo, 'path'):
                    mime_type, _ = mimetypes.guess_type(user.employer_profile.logo.path)
                    prefix = f"data:{mime_type or 'image/png'};base64,"
                    with open(user.employer_profile.logo.path, "rb") as img_file:
                        data['image_base64'] = prefix + base64.b64encode(img_file.read()).decode('utf-8')

        if not data.get('approval_status'):
            data['approval_status'] = 0
        if not data.get('progress_status'):
            data['progress_status'] = 0
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practices/{id}/
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def partial_update(self, request, pk=None, *args, **kwargs):
        # PATCH /api/practices/{id}/
        return self.update(request, pk, partial=True, *args, **kwargs)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def destroy(self, request, pk=None, *args, **kwargs):
        # DELETE /api/practices/{id}/
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def get_practice_user_relations(self, request, pk=None, *args, **kwargs):
        # GET /api/practices/get_practice_user_relations/
        user = request.user
        user_id = user.pk
        if (user.pk):
            # Získej všechny student_practice záznamy pro uživatele
            student_practices = StudentPractice.objects.filter(user=user).select_related('practice', 'practice__employer')
            
            # Získej všechny employer invitations pro uživatele
            from api.models import EmployerInvitation
            employer_invitations = EmployerInvitation.objects.filter(user=user).select_related('practice', 'employer')
            
            # Serializuj student_practice - pouze základní info
            student_practice_data = []
            for sp in student_practices:
                student_practice_data.append({
                    "practice_id": sp.practice.practice_id,
                    "practice_title": sp.practice.title,
                    "company_logo": sp.practice.image_base64,
                    "application_date": sp.application_date,
                    "status": sp.approval_status
                })
            
            # Serializuj employer invitations - pouze základní info
            employer_invitation_data = []
            for ei in employer_invitations:
                employer_invitation_data.append({
                    "practice_id": ei.practice.practice_id if ei.practice else None,
                    "practice_title": ei.practice.title if ei.practice else None,
                    "company_logo": ei.practice.image_base64 if ei.practice else None,
                    "submission_date": ei.submission_date,
                    "status": ei.status
                })
            
            # Vrať zjednodušený JSON
            return Response({
                "student_practices": student_practice_data,
                "employer_invitations": employer_invitation_data
            })
        else:
            return Response({"detail": "Uživatel nebyl nalezen"}, status=status.HTTP_404_NOT_FOUND)

    # PODÁNÍ PŘIHLÁŠKY STUDENTEM
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def apply_student_practice(self, request):
        """
        POST /api/practices/apply_student_practice/
        Vytvoří záznam StudentPractice pro aktuálního uživatele a zadanou praxi.
        Očekává v těle: {"practice": <practice_id>}
        """
        user = request.user
        data = request.data.copy()
        practice_id = data.get("practice")
        if not practice_id:
            return Response({"detail": "Chybí practice (id praxe)"}, status=status.HTTP_400_BAD_REQUEST)
        # Zkontroluj, zda už není přihlášen
        if StudentPractice.objects.filter(practice_id=practice_id, user=user).exists():
            return Response({"detail": "Již jste přihlášen(a) na tuto praxi."}, status=status.HTTP_400_BAD_REQUEST)
        # Nastav povinné hodnoty
        data["user"] = user.pk
        data["application_date"] = date.today()
        data["approval_status"] = ApprovalStatus.PENDING.value
        data["progress_status"] = ProgressStatus.NOT_STARTED.value
        data["hours_completed"] = 0
        data["year"] = date.today().year
        if "semester" not in data:
            data["semester"] = SemesterType.WINTER.value
        serializer = StudentPracticeSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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

    # SEARCH ENDPOINT - pro parametry v requestu
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def search(self, request):
        """
        GET /api/practices/search/
        Vrací praxe s filtry z query parametrů
        """
        queryset = self.queryset.filter(is_active=True)

        subject_id = request.query_params.get("subject")
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        title = request.query_params.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        address = request.query_params.get("address")
        if address:
            queryset = queryset.filter(employer__address__icontains=address)

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RunningPracticeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RunningPracticeSerializer

    def get_queryset(self):
        # noqa: E501  # TODO: https://www.figma.com/proto/6MRkTbxu7nvjVRkxLjm8yi/InternHub-n%C3%A1vrh?node-id=3573-3353&p=f&t=2nsdb5rjnw1qMkGY-0&scaling=scale-down&content-scaling=fixed&page-id=3426%3A3813&starting-point-node-id=3564%3A5736&show-proto-sidebar=1
        # Tohle má být horní část probíhajících praxí, ta spodní se budem muset řešit jinak (asi samostatnej call)
        # Počet přihlášek
        head_of_department = True
        if head_of_department:
            dept_ids = Department.objects.all().values_list("department_id", flat=True).distinct()
        else:
            dept_ids = (
                Department.objects.filter(subjects__user_subjects__user=self.request.user)
                .values_list("department_id", flat=True)
                .distinct()
            )

        students = StudentUser.objects.filter(user_subjects__subject__department_id__in=dept_ids).distinct()
        practices = Practice.objects.filter(
            student_practices__user__in=students,
            is_active=True,
        ).distinct()

        return practices
