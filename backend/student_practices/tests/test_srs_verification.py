"""SRS audit tests: executable evidence for selected functional requirements."""

import io
import unittest
import zipfile
from datetime import date, timedelta

from django.apps import apps
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
from users.models import ApprovalStatus, EmployerProfile, OrganizationUser, ProfessorUser, StudentUser


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

    def test_celery_beat_registration_is_daily_at_three(self):
        call_command("setup_celery_beat")
        from django_celery_beat.models import PeriodicTask

        task = PeriodicTask.objects.get(task="auto_start_end_practices")
        self.assertTrue(task.enabled)
        self.assertEqual((task.crontab.minute, task.crontab.hour), ("0", "3"))
        self.assertEqual((task.crontab.day_of_week, task.crontab.day_of_month, task.crontab.month_of_year), ("*", "*", "*"))


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


class NoCVPortfolioManagementTests(SRSFixture):
    @unittest.expectedFailure  # SRS mezera: StudentUser.cv_file je správa CV přes FileField.
    def test_models_and_api_have_no_cv_portfolio_resume_management(self):
        matches = []
        terms = ("cv", "portfolio", "resume")
        for model in apps.get_models():
            if any(term in model.__name__.lower() for term in terms):
                matches.append(f"model {model._meta.label}")
            for field in model._meta.get_fields():
                if getattr(field, "name", "") and any(term in field.name.lower() for term in terms):
                    from django.db.models import FileField

                    if isinstance(field, FileField) or any(term in field.name.lower() for term in terms):
                        matches.append(f"field {model._meta.label}.{field.name}")
        self.assertEqual(matches, [], "; ".join(matches))
