"""SRS audit tests: executable evidence for selected functional requirements."""

import io
import os
import shutil
import tempfile
import zipfile
from datetime import date, timedelta

from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from notifications.models import Notification
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    Evaluation,
    PracticeRegistration,
    StudentPractice,
)
from student_practices.models import (
    StudentPracticeWorkflowState as State,
)
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SRSFixture(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_name="Audit", department_code="AUD")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="AUD1", department=self.department)
        self.student = StudentUser.objects.create(email="audit-student@test.invalid", first_name="Jan", last_name="Test", is_active=True)
        self.org_user = OrganizationUser.objects.create(email="audit-org@test.invalid", is_active=True)
        self.employer = EmployerProfile.objects.create(
            employer_id=self.org_user.id, company_name="Audit s.r.o.", approval_status=ApprovalStatus.APPROVED
        )
        self.org_user.employer_profile = self.employer
        self.org_user.save()
        self.garant = ProfessorUser.objects.create_user(
            email="audit-garant@test.invalid",
            password="test",
            first_name="Eva",
            last_name="Garant",
            is_active=True,
            department=self.department,
            is_garant_praxe=True,
        )

    def make_practice(self, *, employer=None, start=None, end=None):
        return Practice.objects.create(
            title="Audit praxe",
            employer=employer or self.employer,
            subject=self.subject,
            start_date=start or date.today(),
            end_date=end or date.today() + timedelta(days=30),
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=10,
        )

    def make_sp(self, state, *, practice=None, student=None, start=None, end=None):
        practice = practice or self.make_practice(start=start, end=end)
        return StudentPractice.objects.create(
            user=student or self.student,
            practice=practice,
            start_date=start or practice.start_date,
            end_date=end or practice.end_date,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=state,
        )


class AutomaticLifecycleTests(SRSFixture):
    def test_auto_start_then_end_at_dates(self):
        starts_today = self.make_sp(State.CONTRACTED, start=date.today(), end=date.today() + timedelta(days=4))
        ends_today = self.make_sp(State.STARTED, start=date.today() - timedelta(days=4), end=date.today())
        not_due = self.make_sp(State.CONTRACTED, start=date.today() + timedelta(days=1), end=date.today() + timedelta(days=5))
        call_command("auto_start_end_practices")
        starts_today.refresh_from_db()
        ends_today.refresh_from_db()
        not_due.refresh_from_db()
        self.assertEqual(starts_today.workflow_state, State.STARTED)
        self.assertEqual(ends_today.workflow_state, State.ENDED)
        self.assertEqual(not_due.workflow_state, State.CONTRACTED)

    def test_crontab_is_valid_and_matches_requirements(self):
        """A-27: rozvrh je ve verzovaném crontabu (supercronic); příkazy existují a pokrývají RF-13/14/17a/19a."""
        import re

        from django.core.management import get_commands

        path = settings.BASE_DIR / "crontab"
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 5)
            self.assertEqual(len(parts), 6, line)
            minute, hour, dom, month, dow, command = parts
            for value, upper in ((minute, 59), (hour, 23), (dom, 31), (month, 12), (dow, 7)):
                self.assertRegex(value, r"^(\*|\d+)(/\d+)?$|^\d+(,\d+)*$|^\d+-\d+$")
                if value.isdigit():
                    self.assertLessEqual(int(value), upper)
            m = re.fullmatch(r"python manage\.py (\w+)(?: .*)?", command)
            self.assertIsNotNone(m, command)
            self.assertIn(m.group(1), get_commands())
            entries.append((m.group(1), minute, hour, dow))
        daily = {name: (minute, hour) for name, minute, hour, dow in entries if dow == "*"}
        self.assertEqual(
            daily,
            {
                "auto_close_practices": ("0", "2"),
                "auto_start_end_practices": ("0", "3"),
                "notify_contract_overdue": ("0", "4"),
                "notify_practice_deadlines": ("0", "5"),
            },
        )
        self.assertIn(("cleanup_old_action_logs", "30", "1", "0"), entries)

    def test_scheduled_commands_are_idempotent(self):
        """A-27: opakovaný běh každého příkazu z crontabu nic nezdvojí ani nespadne."""
        from io import StringIO

        from notifications.models import Notification

        self.make_sp(State.CONTRACTED, start=date.today(), end=date.today() + timedelta(days=4))
        for name in (
            "auto_close_practices",
            "auto_start_end_practices",
            "notify_contract_overdue",
            "notify_practice_deadlines",
            "cleanup_old_action_logs",
        ):
            with self.subTest(command=name):
                call_command(name, stdout=StringIO())
                snapshot = (
                    tuple(StudentPractice.objects.order_by("pk").values_list("pk", "workflow_state", "is_cancelled")),
                    Notification.objects.count(),
                )
                call_command(name, stdout=StringIO())
                again = (
                    tuple(StudentPractice.objects.order_by("pk").values_list("pk", "workflow_state", "is_cancelled")),
                    Notification.objects.count(),
                )
                self.assertEqual(snapshot, again)


class DualChannelNotificationTests(SRSFixture):
    def assert_dual_channel(self, verb, recipient):
        self.assertTrue(Notification.objects.filter(verb=verb, recipient=recipient).exists())
        self.assertTrue(any(recipient.email in message.to for message in mail.outbox), f"Chybí e-mail pro {recipient.email}")

    def test_practice_deadline_urgency_emails_and_notifies_in_app(self):
        self.make_sp(State.APPLIED, start=date.today() + timedelta(days=14))
        call_command("notify_practice_deadlines")
        self.assert_dual_channel("PRACTICE_START_URGENCY", self.student)

    def test_overdue_contract_emails_and_notifies_in_app(self):
        sp = self.make_sp(State.AWAITING_CONTRACT)
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=timezone.now() - timedelta(days=10))
        call_command("notify_contract_overdue")
        self.assert_dual_channel("CONTRACT_OVERDUE", self.garant)

    def test_credit_alert_emails_and_notifies_garant_in_app(self):
        sp = self.make_sp(State.ENDED)
        StudentPractice.objects.filter(pk=sp.pk).update(updated_at=timezone.now() - timedelta(days=20))
        call_command("notify_practice_deadlines")
        self.assert_dual_channel("CREDIT_ALERT_GARANT", self.garant)


class DocumentGeneratorTests(SRSFixture):
    def test_all_document_generators_produce_docx(self):
        from student_practices import services

        sp = self.make_sp(State.CONTRACTED)
        generators = (
            services.generate_contract,
            services.generate_content_document,
            services.generate_feedback_form,
            services.generate_report,
        )
        for generator in generators:
            with self.subTest(generator=generator.__name__):
                try:
                    result = generator(sp)
                except (FileNotFoundError, OSError) as exc:
                    if "template" in str(exc).lower() or "šablon" in str(exc).lower():
                        self.skipTest(f"ENV: chybějící šablona dokumentu: {exc}")
                    raise
                result.seek(0)
                with zipfile.ZipFile(io.BytesIO(result.read())) as archive:
                    self.assertIn("word/document.xml", archive.namelist())
                    self.assertTrue(archive.read("word/document.xml"))


class OrganizationEvaluationScopeTests(SRSFixture):
    def test_registration_two_organizations_create_and_scope_evaluations(self):
        org2_user = OrganizationUser.objects.create(email="audit-org2@test.invalid", is_active=True)
        org2 = EmployerProfile.objects.create(
            employer_id=org2_user.id,
            company_name="Druhá s.r.o.",
            approval_status=ApprovalStatus.APPROVED,
        )
        org2_user.employer_profile = org2
        org2_user.save()
        registration = PracticeRegistration.objects.create(student=self.student, subject=self.subject, year=date.today().year)
        sp1 = self.make_sp(State.ENDED, practice=self.make_practice(employer=self.employer))
        sp2 = self.make_sp(State.ENDED, practice=self.make_practice(employer=org2))
        sp1.registration = registration
        sp1.save(update_fields=["registration"])
        sp2.registration = registration
        sp2.save(update_fields=["registration"])
        client = APIClient()

        def payload(sp):
            return {
                "student_practice_id": sp.pk,
                "expertise_rating": 5,
                "expertise_comment": "Audit",
                "communication_rating": 4,
                "communication_comment": "Audit",
                "initiative_rating": 5,
                "initiative_comment": "Audit",
                "overall_comment": "Audit",
                "pdf_file": SimpleUploadedFile("audit.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            }

        client.force_authenticate(self.org_user)
        own = client.post("/api/student-practices/evaluations/", payload(sp1), format="multipart")
        self.assertEqual(own.status_code, 201, own.data)
        client.force_authenticate(org2_user)
        foreign_create = client.post("/api/student-practices/evaluations/", payload(sp1), format="multipart")
        self.assertIn(foreign_create.status_code, (403, 404))
        own2 = client.post("/api/student-practices/evaluations/", payload(sp2), format="multipart")
        self.assertEqual(own2.status_code, 201, own2.data)
        own_eval = Evaluation.objects.get(student_practice=sp2)
        changed = client.patch(f"/api/student-practices/evaluations/{own_eval.pk}/", {"expertise_comment": "changed"}, format="json")
        self.assertNotEqual(changed.status_code, 404)
        foreign_eval = Evaluation.objects.get(student_practice=sp1)
        foreign_read = client.get(f"/api/student-practices/evaluations/{foreign_eval.pk}/")
        self.assertEqual(foreign_read.status_code, 404)
        foreign_change = client.patch(
            f"/api/student-practices/evaluations/{foreign_eval.pk}/",
            {"expertise_comment": "hacked"},
            format="json",
        )
        self.assertIn(foreign_change.status_code, (403, 404))
        foreign_eval.refresh_from_db()
        self.assertEqual(foreign_eval.expertise_comment, "Audit")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="srs_cv_"), STORAGE_ROOT=tempfile.mkdtemp(prefix="srs_cv_"))
class OptionalCVAttachmentTests(SRSFixture):
    """RNF-08: plnohodnotná správa CV/portfolia se neimplementuje.

    Zůstává jen volitelná PDF příloha profilu (``StudentUser.cv_file``):
    nepovinná, pouze PDF, stažitelná jen oprávněnými osobami.
    """

    PROFILE_URL = "/api/users/profile/"

    def setUp(self):
        super().setUp()
        # STORAGE_ROOT i MEDIA_ROOT musí ukazovat do stejné složky
        self.root = settings.MEDIA_ROOT
        override = override_settings(STORAGE_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.client_student = APIClient()
        self.client_student.force_authenticate(user=self.student)

    def _upload(self, name="zivotopis.pdf", content=b"%PDF-1.4 test"):
        return self.client_student.patch(
            self.PROFILE_URL,
            {"cv_file": SimpleUploadedFile(name, content, content_type="application/pdf")},
            format="multipart",
        )

    def test_no_cv_or_portfolio_management_models(self):
        """Neexistuje model pro správu CV/portfolia; pole smí být jen volitelné cv_file a resume na StudentUser."""
        terms = ("cv", "portfolio", "resume")
        models_found = [m._meta.label for m in apps.get_models() if any(t in m.__name__.lower() for t in terms)]
        self.assertEqual(models_found, [])
        fields_found = sorted(
            f"{m._meta.label}.{f.name}"
            for m in apps.get_models()
            for f in m._meta.get_fields()
            if any(t in getattr(f, "name", "").lower() for t in terms)
        )
        # cv_file = volitelná PDF příloha, resume = volitelný krátký textový popis u profilu
        self.assertEqual(fields_found, ["users.StudentUser.cv_file", "users.StudentUser.resume"])

    def test_cv_is_optional(self):
        """Student bez CV existuje a může si upravit profil bez nahrání souboru."""
        self.assertFalse(self.student.cv_file)
        response = self.client_student.patch(self.PROFILE_URL, {"first_name": "Honza"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Honza")
        self.assertFalse(self.student.cv_file)

    def test_only_pdf_is_accepted(self):
        response = self._upload(name="zivotopis.exe", content=b"MZ")
        self.assertEqual(response.status_code, 400)
        self.student.refresh_from_db()
        self.assertFalse(self.student.cv_file)

    def test_upload_and_download_by_authorised_users_only(self):
        """Nahrání → stažení vlastníkem; cizí student a cizí firma dostanou 404 (A-20: neprozrazuje existenci)."""
        response = self._upload()
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.cv_file.name.endswith(".pdf"))
        rel = f"/api/files/{self.student.cv_file.name}/"

        own = self.client_student.get(rel)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(b"".join(own.streaming_content), b"%PDF-1.4 test")

        stranger = StudentUser.objects.create(email="stranger@test.invalid", is_active=True)
        client = APIClient()
        client.force_authenticate(user=stranger)
        self.assertEqual(client.get(rel).status_code, 404)

        # zaměstnavatel bez přihlášky studenta CV nevidí, s přihláškou ano
        client.force_authenticate(user=self.org_user)
        self.assertEqual(client.get(rel).status_code, 404)
        self.make_sp(State.APPLIED)
        self.assertEqual(client.get(rel).status_code, 200)

    def test_replacing_cv_removes_previous_file(self):
        self._upload(name="stary.pdf")
        self.student.refresh_from_db()
        old_path = self.student.cv_file.path
        self.assertTrue(os.path.exists(old_path))
        self._upload(name="novy.pdf", content=b"%PDF-1.4 novy")
        self.assertFalse(os.path.exists(old_path))
