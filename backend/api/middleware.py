from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from student_practices.models import StudentPractice, UploadedDocument
from users.models import StudentUser


class DocumentPermissionMiddleware(MiddlewareMixin):
    """Restrict document file and profile image access to authorised users only."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        storage_prefix = f"/{settings.STORAGE_URL}"

        if not request.path.startswith(storage_prefix):
            return None

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        documents_prefix = f"{storage_prefix}documents/"
        images_prefix = f"{storage_prefix}images/"
        cvs_prefix = f"{storage_prefix}documents/cvs/"

        if request.path.startswith(documents_prefix) and not request.path.startswith(cvs_prefix):
            return self._check_document_access(request)

        if request.path.startswith(cvs_prefix):
            return self._check_cv_access(request)

        if request.path.startswith(images_prefix):
            return self._check_image_access(request)

        return None

    def _check_document_access(self, request):
        rel_path = request.path.lstrip("/")
        storage_prefix = settings.STORAGE_URL.rstrip("/") + "/"
        if rel_path.startswith(storage_prefix):
            rel_path = rel_path[len(storage_prefix) :]

        doc = UploadedDocument.objects.filter(document=rel_path).only("document_id").first()
        if doc is None:
            raise Http404()

        has_access = (
            StudentPractice.objects.filter(
                Q(contract_document_id=doc.document_id) | Q(content_document_id=doc.document_id) | Q(feedback_document_id=doc.document_id)
            )
            .filter(Q(user=request.user) | Q(practice__contact_user=request.user) | Q(practice__employer__organization_users=request.user))
            .exists()
        )

        if not has_access:
            raise Http404()

        return None

    def _check_cv_access(self, request):
        rel_path = request.path.lstrip("/")
        student = StudentUser.objects.filter(cv_file=rel_path).only("user_id").first()
        if student is None:
            raise Http404()
        if student.user_id == request.user.user_id:
            return None
        if request.user.is_superuser:
            return None
        from users.models import DepartmentRole, ProfessorUser, UserSubjectType

        if isinstance(request.user, ProfessorUser):
            from subject.models import Subject

            if Subject.objects.filter(
                user_subjects__user=request.user,
                user_subjects__role=UserSubjectType.Professor,
                practices__student_practices__user=student,
            ).exists():
                return None
            if (
                request.user.department_role == DepartmentRole.HEAD
                and Subject.objects.filter(
                    user_subjects__user=request.user,
                    department__professor_users=request.user,
                    practices__student_practices__user=student,
                ).exists()
            ):
                return None

        raise Http404()

    def _check_image_access(self, request):
        rel_path = request.path.lstrip("/")
        student = StudentUser.objects.filter(profile_picture=rel_path).only("user_id").first()
        if student is None:
            employer_logo_prefix = f"{settings.STORAGE_URL}images/logos/"
            if request.path.startswith(f"/{employer_logo_prefix}"):
                return None
            raise Http404()
        return None
