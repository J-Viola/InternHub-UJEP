from datetime import date, datetime

from api.decorators import role_required
from api.models import (
    ApprovalStatus,
    Department,
    EmployerInvitation,
    EmployerInvitationStatus,
    OrganizationRole,
    Practice,
    ProfessorUser,
    ProgressStatus,
    StudentPractice,
    StudentUser,
    UserSubjectType,
)
from api.serializers import PracticeSerializer
from api.views import StandardResultsSetPagination
from drf_spectacular.utils import OpenApiResponse, extend_schema
from practices.serializers import (
    EndDateRequestSerializer,
    EndDateResponseSerializer,
    OrganizationPracticeSerializer,
    PracticeApprovalSerializer,
    PracticeApprovalStatusSerializer,
    RunningPracticeSerializer,
    StudentPracticeSerializer,
)
from practices.utils import calculate_end_date
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import StagRoleEnum


# -------------------------------------------------------------
# PracticeViewSet – CRUD a správa praxí, včetně přihlášení
# -------------------------------------------------------------
class PracticeViewSet(viewsets.ModelViewSet):

    queryset = Practice.objects.all().select_related("employer")
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
        user_id = request.user.id

        contact_user_info = None
        student_practice_documents = []
        if practice_obj.contact_user:
            contact_user_info = {
                "user_id": practice_obj.contact_user.user_id,
                "username": practice_obj.contact_user.username,
                "first_name": practice_obj.contact_user.first_name,
                "last_name": practice_obj.contact_user.last_name,
                "email": practice_obj.contact_user.email,
                "phone": practice_obj.contact_user.phone,
            }
            try:
                student = StudentUser.objects.get(user_id=user_id)
            except StudentUser.DoesNotExist:
                student = None
            if student:
                approved_practices = StudentPractice.objects.filter(
                    user=student, practice=practice_obj, approval_status=ApprovalStatus.APPROVED
                )
                for sp in approved_practices:
                    if sp.contract_document_id:
                        student_practice_documents.append({"id": sp.contract_document_id, "type": "contract"})
                    if sp.content_document_id:
                        student_practice_documents.append({"id": sp.content_document_id, "type": "content"})
                    if sp.feedback_document_id:
                        student_practice_documents.append({"id": sp.feedback_document_id, "type": "feedback"})

        response_data = serializer.data
        response_data["contact_user_info"] = contact_user_info
        response_data["student_practice_documents"] = student_practice_documents

        return Response(response_data)

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
        if not data.get("employer_id") and hasattr(user, "employer_profile") and user.employer_profile:
            data["employer_id"] = user.employer_profile.employer_id
            # Nastav logo z employer profilu
            if user.employer_profile.logo:
                import base64
                import mimetypes

                if hasattr(user.employer_profile.logo, "path"):
                    mime_type, _ = mimetypes.guess_type(user.employer_profile.logo.path)
                    prefix = f"data:{mime_type or 'image/png'};base64,"
                    with open(user.employer_profile.logo.path, "rb") as img_file:
                        data["image_base64"] = prefix + base64.b64encode(img_file.read()).decode("utf-8")

        if not data.get("approval_status"):
            data["approval_status"] = 0
        if not data.get("progress_status"):
            data["progress_status"] = 0
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @role_required([OrganizationRole.OWNER, OrganizationRole.INSERTER, StagRoleEnum.VY])
    def update(self, request, pk=None, *args, **kwargs):
        # PUT /api/practices/{id}/
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data.copy()

        # Fix date format for start_date and end_date
        for date_field in ["start_date", "end_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    if "." in data[date_field]:
                        parsed = datetime.strptime(data[date_field], "%d.%m.%Y")
                        data[date_field] = parsed.strftime("%Y-%m-%d")
                except Exception:
                    pass

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
        if user.pk:
            # Získej všechny student_practice záznamy pro uživatele
            student_practices = StudentPractice.objects.filter(user=user).select_related("practice", "practice__employer")

            # Získej všechny employer invitations pro uživatele
            employer_invitations = EmployerInvitation.objects.filter(user=user, status=EmployerInvitationStatus.PENDING).select_related(
                "practice", "employer"
            )

            # Serializuj student_practice - pouze základní info
            student_practice_data = []
            for sp in student_practices:
                student_practice_data.append(
                    {
                        "student_practice_id": sp.student_practice_id,
                        "practice_id": sp.practice.practice_id,
                        "practice_title": sp.practice.title,
                        "company_logo": sp.practice.image_base64,
                        "application_date": sp.application_date,
                        "status": sp.approval_status,
                    }
                )

            # Serializuj employer invitations - pouze základní info
            employer_invitation_data = []
            for ei in employer_invitations:
                employer_invitation_data.append(
                    {
                        "invitation_id": ei.invitation_id,
                        "practice_id": ei.practice.practice_id if ei.practice else None,
                        "practice_title": ei.practice.title if ei.practice else None,
                        "company_logo": ei.practice.image_base64 if ei.practice else None,
                        "submission_date": ei.submission_date,
                        "status": ei.status,
                    }
                )

            # Vrať zjednodušený JSON
            return Response({"student_practices": student_practice_data, "employer_invitations": employer_invitation_data})
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

        practice = Practice.objects.filter(practice_id=practice_id, is_active=True).first()
        if not practice:
            return Response({"detail": "Praxe nenalezena nebo není aktivní."}, status=status.HTTP_404_NOT_FOUND)
        # Nastav povinné hodnoty
        data["user"] = user.pk
        data["application_date"] = date.today()
        data["approval_status"] = ApprovalStatus.PENDING.value
        data["progress_status"] = ProgressStatus.NOT_STARTED.value
        data["hours_completed"] = 0
        data["year"] = date.today().year
        data["start_date"] = practice.start_date.strftime("%d.%m.%Y")
        data["end_date"] = practice.end_date.strftime("%d.%m.%Y")
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

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.AllowAny], url_path="by_employer_profile/(?P<employer_id>[^/.]+)"
    )
    def by_employer_profile(self, request, employer_id):
        """
        GET /api/practices/by_employer_profile/{employer_id}
        Vrací praxe patřící k dané organizaci
        """
        practices = Practice.objects.filter(employer=employer_id, is_active=True).order_by("start_date")
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def organization_practices(self, request):
        """
        GET /api/practices/organization_practices/
        Vrací všechny praxe vytvořené organizací přihlášeného uživatele
        """
        user = request.user

        # Kontrola, zda je uživatel organizace
        if not hasattr(user, "employer_profile") or not user.employer_profile:
            return Response(
                {"detail": "Přístup odepřen. Pouze uživatelé organizací mohou přistupovat k tomuto endpointu."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Získání praxí podle employer_profile uživatele
        practices = (
            Practice.objects.filter(employer=user.employer_profile)
            .select_related("subject", "subject__department", "contact_user")
            .prefetch_related("student_practices")
            .order_by("-created_at")
        )

        serializer = OrganizationPracticeSerializer(practices, many=True)
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

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def by_user_department(self, request):
        """
        GET /api/practices/by_user_department/
        Vrátí praxe podle katedry přihlášeného uživatele rozdělené na schválené a čekající na schválení.
        """
        user_id = request.user.id
        if not user_id:
            return Response({"detail": "Chybí user_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Nejprve zkus najít katedru přes ProfessorUser
        professor = ProfessorUser.objects.filter(user_ptr_id=user_id).first()
        if professor and professor.department:
            dept_ids = [professor.department.department_id]
        else:
            # Pokud není profesor, použij původní logiku přes UserSubject
            dept_ids = (
                Department.objects.filter(
                    subjects__user_subjects__user_id=user_id,
                    subjects__user_subjects__role__in=[UserSubjectType.Student.value, UserSubjectType.Professor.value],
                )
                .values_list("department_id", flat=True)
                .distinct()
            )

        if not dept_ids:
            return Response({"detail": "Uživatel nemá přiřazenou žádnou katedru."}, status=status.HTTP_404_NOT_FOUND)

        # Najdi všechny praxe, které jsou přes předmět přiřazeny do těchto kateder
        practices = Practice.objects.filter(subject__department_id__in=dept_ids, is_active=True)

        # Rozděl na schválené a čekající na schválení
        approved = practices.filter(approval_status=ApprovalStatus.APPROVED)
        to_approve = practices.filter(approval_status=ApprovalStatus.PENDING)

        serializer = PracticeSerializer
        approved_data = serializer(approved, many=True, context={"request": request}).data
        to_approve_data = serializer(to_approve, many=True, context={"request": request}).data

        def enrich_contact_user(practice):
            user = getattr(practice, "contact_user", None)
            if user:
                return {
                    "user_id": user.user_id,
                    "username": getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "last_name": getattr(user, "last_name", None),
                    "email": getattr(user, "email", None),
                    "phone": getattr(user, "phone", None),
                }
            return None

        for item in approved_data:
            practice = approved.get(practice_id=item["practice_id"])
            item["contact_user_info"] = enrich_contact_user(practice)
        for item in to_approve_data:
            practice = to_approve.get(practice_id=item["practice_id"])
            item["contact_user_info"] = enrich_contact_user(practice)

        return Response({"approved_practices": approved_data, "to_approve_practices": to_approve_data})


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


class PracticesForApprovingListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PracticeApprovalSerializer

    def get_queryset(self):
        dept_ids = Department.objects.filter(professor_users=self.request.user).values_list("department_id", flat=True).distinct()

        practices_to_approve = Practice.objects.filter(subject__department_id__in=dept_ids, approval_status=ApprovalStatus.PENDING)

        print(f"Found {practices_to_approve.count()} for approval")

        return practices_to_approve


class ChangePendingView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PracticeApprovalStatusSerializer

    def post(self, request, *args, **kwargs):
        """
        POST /api/practices/{id}/change-pending
        Changes approval status of a practice
        """
        practice_id = kwargs.get("id")
        try:
            practice_obj = Practice.objects.get(pk=practice_id)
        except Practice.DoesNotExist:
            return Response({"detail": "Praxe nenalezena"}, status=status.HTTP_404_NOT_FOUND)
        if practice_obj.approval_status != ApprovalStatus.PENDING:
            return Response({"detail": "Praxe je již schválena/zamítnuta"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        approval_status = ApprovalStatus.get(name_or_numeric=serializer.validated_data.get("approval_status"))
        practice_obj.approval_status = approval_status
        practice_obj.save()
        serializer = PracticeSerializer(practice_obj)
        return Response(serializer.data)


class GetEndDateView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Calculate end date of practice",
        description="Returns the calculated end date based on the start date and coefficient",
        request=EndDateRequestSerializer,
        responses={
            200: EndDateResponseSerializer,
            400: OpenApiResponse(description="Bad request"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = EndDateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start_date = serializer.validated_data["start_date"]
        coefficient = serializer.validated_data["coefficient"]
        end_date = calculate_end_date(start_date, coefficient)
        output = {"end_date": end_date}
        return Response(EndDateResponseSerializer(output).data, status=status.HTTP_200_OK)
