from datetime import date, timedelta
from unittest import mock

import pytest
from django.core import mail
from django.test import TestCase

from notifications.models import Notification, NotificationType
from notifications.services import EmailService, NotificationService
from practices.models import Practice, ProgressStatus
from student_practices.models import Evaluation, StudentPractice
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
    UserSubject,
    UserSubjectType,
)


class EmailServiceTest(TestCase):
    def setUp(self):
        self.employer = EmployerProfile.objects.create(company_name="Test Org", approval_status=ApprovalStatus.APPROVED)
        self.org_user = OrganizationUser.objects.create(
            email="org@test.com",
            employer_profile=self.employer,
            first_name="Org",
            last_name="Contact",
            organization_role=OrganizationRole.OWNER,
        )
        self.student = StudentUser.objects.create(email="student@test.com", first_name="John", last_name="Doe")
        self.professor = ProfessorUser.objects.create(email="prof@test.com", first_name="Jane", last_name="Doe")
        self.practice = Practice.objects.create(
            title="Test Practice",
            employer=self.employer,
            contact_user=self.org_user,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            coefficient=1.0,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 1),
        )
        # Create a Subject and assign professor
        from subject.models import Subject

        self.subject = Subject.objects.create(subject_name="Test Subject", subject_code="TS101")
        self.practice.subject = self.subject
        self.practice.save()

        UserSubject.objects.create(user=self.professor, subject=self.subject, role=UserSubjectType.Professor)

        self.student_practice = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 1),
        )
        from student_practices.models import DocumentType, UploadedDocument

        self.document = UploadedDocument.objects.create(
            document_type=DocumentType.CONTRACT,
        )
        self.student_practice.contract_document = self.document
        self.student_practice.save()

    def test_notify_org_new_application(self):
        EmailService.notify_org_new_application(self.student_practice)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Nová přihláška na praxi: {self.practice.title}")
        self.assertIn("John Doe", mail.outbox[0].body)
        self.assertIn("org@test.com", mail.outbox[0].to)

    def test_notify_student_application_status_approved(self):
        self.student_practice.approval_status = ApprovalStatus.APPROVED
        EmailService.notify_student_application_status(self.student_practice)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Schválena", mail.outbox[0].subject)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_student_application_status_rejected(self):
        self.student_practice.approval_status = ApprovalStatus.REJECTED
        EmailService.notify_student_application_status(self.student_practice)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Zamítnuta", mail.outbox[0].subject)

    def test_notify_org_practice_status_approved(self):
        self.practice.approval_status = ApprovalStatus.APPROVED
        EmailService.notify_org_practice_status(self.practice)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Schválena", mail.outbox[0].subject)
        self.assertIn("org@test.com", mail.outbox[0].to)

    def test_notify_student_document_review(self):
        from student_practices.models import DocumentStatus

        self.document.status = DocumentStatus.REJECTED
        self.document.review_note = "Please fix formatting."
        EmailService.notify_student_document_review(self.document)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("zamítnut", mail.outbox[0].subject)
        self.assertIn("Please fix formatting.", mail.outbox[0].body)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_professors_document_upload(self):
        EmailService.notify_professors_document_upload(self.document)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Nový dokument", mail.outbox[0].subject)
        self.assertIn("prof@test.com", mail.outbox[0].to)

    def test_notify_student_invitation(self):
        from student_practices.models import (
            EmployerInvitation,
            EmployerInvitationStatus,
        )

        invitation = EmployerInvitation.objects.create(
            employer=self.employer,
            user=self.student,
            practice=self.practice,
            status=EmployerInvitationStatus.PENDING,
        )
        EmailService.notify_student_invitation(invitation)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Pozvánka na praxi", mail.outbox[0].subject)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_password_reset(self):
        EmailService.notify_password_reset(self.student, "http://test.com/reset")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Obnova hesla", mail.outbox[0].subject)
        self.assertIn("http://test.com/reset", mail.outbox[0].body)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_password_changed(self):
        EmailService.notify_password_changed(self.student)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("heslo bylo změněno", mail.outbox[0].subject)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_org_welcome(self):
        EmailService.notify_org_welcome(self.org_user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Vítejte v InternHub", mail.outbox[0].subject)
        self.assertIn("org@test.com", mail.outbox[0].to)

    def test_notify_org_profile_status(self):
        self.employer.approval_status = ApprovalStatus.APPROVED
        EmailService.notify_org_profile_status(self.employer)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("profilu organizace", mail.outbox[0].subject)
        self.assertIn("schválen", mail.outbox[0].body)
        self.assertIn("org@test.com", mail.outbox[0].to)

    # --- M-M4-2: Cancellation email tests ---

    def test_notify_student_cancellation(self):
        reason = "Praxe byla zrušena organizací"
        EmailService.notify_student_cancellation(self.student, self.student_practice, reason)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("přihláška na praxi byla zrušena", mail.outbox[0].subject)
        self.assertIn(reason, mail.outbox[0].body)
        self.assertIn(self.practice.title, mail.outbox[0].body)
        self.assertIn("student@test.com", mail.outbox[0].to)

    def test_notify_student_cancellation_no_email(self):
        """Should silently return if user has no email."""
        self.student.email = ""
        self.student.save()
        EmailService.notify_student_cancellation(self.student, self.student_practice, "reason")
        self.assertEqual(len(mail.outbox), 0)

    def test_notify_org_cancellation(self):
        reason = "Student odstoupil"
        EmailService.notify_org_cancellation(self.employer, self.student_practice, reason)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("přihláška studenta na praxi byla zrušena", mail.outbox[0].subject.lower())
        self.assertIn(reason, mail.outbox[0].body)
        self.assertIn("John Doe", mail.outbox[0].body)
        self.assertIn("org@test.com", mail.outbox[0].to)

    def test_notify_org_cancellation_no_contact(self):
        """Should silently return if no org contact."""
        self.practice.contact_user = None
        self.practice.save()
        EmailService.notify_org_cancellation(self.employer, self.student_practice, "reason")
        self.assertEqual(len(mail.outbox), 0)


# ---------------------------------------------------------------------------
# resolve_garant_recipients + nové notify metody
# ---------------------------------------------------------------------------


class TestResolveGarantRecipients:
    """Pokrytí všech 3 větví rezoluce garanta."""

    def test_subject_manager_preferred(self, db, practice, subject):
        """Větev 1: practice.subject.subject_manager má přednost."""
        manager = ProfessorUser.objects.create(
            email="manager@test.com",
            first_name="Man",
            last_name="Ager",
            department=subject.department,
        )
        subject.subject_manager = manager
        subject.save()

        recipients = NotificationService.resolve_garant_recipients(practice)
        assert recipients == [manager]

    def test_garant_praxe_department(self, db, practice, subject, department):
        """Větev 2: subject_manager None → garanti praxe na katedře."""
        garant = ProfessorUser.objects.create(
            email="garant@test.com",
            first_name="Gar",
            last_name="Ant",
            department=department,
            is_garant_praxe=True,
        )
        # Ne-garant profesor katedry se v této větvi nesmí objevit
        ProfessorUser.objects.create(
            email="teacher@test.com",
            first_name="Tea",
            last_name="Cher",
            department=department,
            is_garant_praxe=False,
        )

        recipients = NotificationService.resolve_garant_recipients(practice)
        assert recipients == [garant]

    def test_fallback_department_professors(self, db, practice, subject, department):
        """Větev 3: bez subject_manager a bez garanta → všichni profesoři katedry."""
        prof1 = ProfessorUser.objects.create(email="prof1@test.com", first_name="A", last_name="B", department=department)
        prof2 = ProfessorUser.objects.create(email="prof2@test.com", first_name="C", last_name="D", department=department)

        recipients = NotificationService.resolve_garant_recipients(practice)
        assert set(recipients) == {prof1, prof2}

    def test_accepts_student_practice(self, db, practice, subject):
        """StudentPractice se převede přes FK practice na rezoluci."""
        manager = ProfessorUser.objects.create(
            email="manager@test.com",
            first_name="Man",
            last_name="Ager",
            department=subject.department,
        )
        subject.subject_manager = manager
        subject.save()

        sp = StudentPractice.objects.create(
            user=None,
            practice=practice,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        assert NotificationService.resolve_garant_recipients(sp) == [manager]

    def test_no_subject_returns_empty(self, db, employer_profile):
        p = Practice.objects.create(
            title="Bez předmětu",
            employer=employer_profile,
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
        )
        assert NotificationService.resolve_garant_recipients(p) == []

    def test_none_returns_empty(self, db):
        assert NotificationService.resolve_garant_recipients(None) == []


@pytest.fixture
def garant_env(db, practice, subject, department, student_user, org_user):
    """Garant katedry (is_garant_praxe) + StudentPractice s plnou vazbou na praxi."""
    garant = ProfessorUser.objects.create(
        email="garant@test.com",
        first_name="Gar",
        last_name="Ant",
        department=department,
        is_garant_praxe=True,
    )
    practice.contact_user = org_user
    practice.save()
    sp = StudentPractice.objects.create(
        user=student_user,
        practice=practice,
        approval_status=ApprovalStatus.PENDING,
        progress_status=ProgressStatus.NOT_STARTED,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )
    return {"sp": sp, "garant": garant, "practice": practice, "org_user": org_user}


class TestNewNotificationServiceMethods:
    """Každá nová notify metoda: in-app notifikace + e-mail přes EmailService (mock)."""

    def test_notify_garant_new_application(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        with mock.patch.object(EmailService, "notify_garant_new_application_email") as mocked:
            NotificationService.notify_garant_new_application(sp)
            mocked.assert_called_once_with(sp)

        notif = Notification.objects.get(verb="NEW_APPLICATION_GARANT")
        assert notif.recipient == garant
        assert notif.target == sp
        assert notif.actor == sp.user
        assert "Testovací stáž" in notif.message
        assert len(mail.outbox) == 0  # e-mail jde přes EmailService metodu, ne genericky

    def test_notify_garant_cancellation(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        with mock.patch.object(EmailService, "notify_garant_cancellation_email") as mocked:
            NotificationService.notify_garant_cancellation(sp)
            mocked.assert_called_once_with(sp)

        notif = Notification.objects.get(verb="CANCELLATION_GARANT")
        assert notif.recipient == garant
        assert notif.target == sp
        assert len(mail.outbox) == 0

    def test_notify_garant_evaluation_submitted(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        evaluation = Evaluation.objects.create(student_practice=sp)
        with mock.patch.object(EmailService, "notify_garant_evaluation_submitted_email") as mocked:
            NotificationService.notify_garant_evaluation_submitted(evaluation)
            mocked.assert_called_once_with(evaluation)

        notif = Notification.objects.get(verb="EVALUATION_SUBMITTED")
        assert notif.recipient == garant
        assert notif.target == evaluation
        assert len(mail.outbox) == 0

    def test_notify_org_allocation(self, garant_env):
        sp = garant_env["sp"]
        org_user = garant_env["org_user"]
        with mock.patch.object(EmailService, "notify_org_allocation_email") as mocked:
            NotificationService.notify_org_allocation(sp)
            mocked.assert_called_once_with(sp)

        notif = Notification.objects.get(verb="ALLOCATION_ORG")
        assert notif.recipient == org_user  # practice.contact_user
        assert notif.target == sp
        assert len(mail.outbox) == 0

    def test_notify_org_allocation_without_contact(self, garant_env):
        sp = garant_env["sp"]
        sp.practice.contact_user = None
        sp.practice.save()
        with mock.patch.object(EmailService, "notify_org_allocation_email") as mocked:
            NotificationService.notify_org_allocation(sp)
            mocked.assert_not_called()
        assert Notification.objects.filter(verb="ALLOCATION_ORG").count() == 0

    def test_notify_export_ready(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        with mock.patch.object(EmailService, "notify_export_ready_email") as mocked:
            NotificationService.notify_export_ready(garant, sp)
            mocked.assert_called_once_with(garant, sp, download_url=None)

        notif = Notification.objects.get(verb="EXPORT_READY")
        assert notif.recipient == garant
        assert notif.target == sp
        assert notif.url == ""
        assert len(mail.outbox) == 0

    def test_notify_export_ready_no_target(self, garant_env):
        garant = garant_env["garant"]
        with mock.patch.object(EmailService, "notify_export_ready_email") as mocked:
            NotificationService.notify_export_ready(garant, None)
            mocked.assert_called_once_with(garant, None, download_url=None)

        notif = Notification.objects.get(verb="EXPORT_READY")
        assert notif.recipient == garant
        assert notif.target is None

    def test_notify_export_ready_with_download_url(self, garant_env):
        """EXPORT_READY s download_url → url uložena v Notification i serializované."""
        from notifications.serializers import NotificationSerializer

        garant = garant_env["garant"]
        download_url = "/api/export/download/123/"
        with mock.patch.object(EmailService, "notify_export_ready_email") as mocked:
            NotificationService.notify_export_ready(garant, None, download_url=download_url)
            mocked.assert_called_once_with(garant, None, download_url=download_url)

        notif = Notification.objects.get(verb="EXPORT_READY")
        assert notif.url == download_url
        assert download_url in notif.message

        data = NotificationSerializer(notif).data
        assert data["url"] == download_url
        # target None → target_url None, url použitelná FE
        assert data["target_url"] is None

    def test_notify_garant_contract_overdue(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        with mock.patch.object(EmailService, "notify_garant_contract_overdue_email") as mocked:
            NotificationService.notify_garant_contract_overdue(sp)
            mocked.assert_called_once_with(sp)

        notif = Notification.objects.get(verb="CONTRACT_OVERDUE")
        assert notif.recipient == garant
        assert notif.target == sp
        assert len(mail.outbox) == 0


class TestNewEmailServiceMethods:
    """Přímé testy e-mailů (mail.outbox) — předmět i příjemci dle existujícího stylu."""

    def test_notify_garant_new_application_email(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        EmailService.notify_garant_new_application_email(sp)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "Testovací stáž" in mail.outbox[0].subject

    def test_notify_garant_cancellation_email(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        EmailService.notify_garant_cancellation_email(sp)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "Storno" in mail.outbox[0].subject

    def test_notify_garant_evaluation_submitted_email(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        evaluation = Evaluation.objects.create(student_practice=sp)
        EmailService.notify_garant_evaluation_submitted_email(evaluation)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "Evaluace" in mail.outbox[0].subject

    def test_notify_org_allocation_email(self, garant_env):
        sp = garant_env["sp"]
        org_user = garant_env["org_user"]
        org_user.organization_role = OrganizationRole.OWNER
        org_user.save()
        EmailService.notify_org_allocation_email(sp)
        assert len(mail.outbox) == 1
        assert org_user.email in mail.outbox[0].to
        assert "Alokace" in mail.outbox[0].subject

    def test_notify_export_ready_email(self, garant_env):
        garant = garant_env["garant"]
        EmailService.notify_export_ready_email(garant)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "Export" in mail.outbox[0].subject

    def test_notify_garant_contract_overdue_email(self, garant_env):
        sp = garant_env["sp"]
        garant = garant_env["garant"]
        EmailService.notify_garant_contract_overdue_email(sp)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "Prodlení" in mail.outbox[0].subject


# ---------------------------------------------------------------------------
# registrace firem → garanti — NEW_ORG_REGISTRATION + MANUAL_REGISTRATION
# ---------------------------------------------------------------------------


@pytest.fixture
def org_registration_env(db, department):
    """Garant praxe + nově registrovaná firma (OrganizationUser + EmployerProfile)."""
    garant = ProfessorUser.objects.create(
        email="garant@test.com",
        first_name="Gar",
        last_name="Ant",
        department=department,
        is_garant_praxe=True,
    )
    profile = EmployerProfile.objects.create(
        company_name="New Co",
        ico="12345678",
        approval_status=ApprovalStatus.PENDING,
    )
    org_user = OrganizationUser.objects.create(
        email="org-new@test.com",
        first_name="Org",
        last_name="User",
        employer_profile=profile,
    )
    return {"garant": garant, "profile": profile, "org_user": org_user}


class TestRegistrationNotificationServiceMethods:
    """nové notifikační metody pro registrace firem (in-app + e-mail)."""

    def test_notify_garants_new_org_registration(self, org_registration_env):
        org_user = org_registration_env["org_user"]
        garant = org_registration_env["garant"]
        with mock.patch.object(EmailService, "notify_garants_new_org_registration_email") as mocked:
            NotificationService.notify_garants_new_org_registration(org_user)
            mocked.assert_called_once_with(org_user)

        notif = Notification.objects.get(verb="NEW_ORG_REGISTRATION")
        assert notif.recipient == garant
        assert notif.target == org_user.employer_profile
        assert "New Co" in notif.message
        assert len(mail.outbox) == 0

    def test_notify_garants_new_org_registration_without_profile(self, org_registration_env):
        org_user = OrganizationUser.objects.create(email="org-no-profile@test.com", first_name="A", last_name="B")
        with mock.patch.object(EmailService, "notify_garants_new_org_registration_email") as mocked:
            NotificationService.notify_garants_new_org_registration(org_user)
            mocked.assert_not_called()
        assert Notification.objects.filter(verb="NEW_ORG_REGISTRATION").count() == 0

    def test_notify_garants_manual_registration(self, org_registration_env):
        profile = org_registration_env["profile"]
        garant = org_registration_env["garant"]
        with mock.patch.object(EmailService, "notify_garants_manual_registration_email") as mocked:
            NotificationService.notify_garants_manual_registration(profile)
            mocked.assert_called_once_with(profile)

        notif = Notification.objects.get(verb="MANUAL_REGISTRATION")
        assert notif.recipient == garant
        assert notif.target == profile
        assert notif.notification_type == NotificationType.WARNING
        assert "ručně" in notif.message
        assert len(mail.outbox) == 0


class TestRegistrationEmailServiceMethods:
    """přímé e-mailové testy pro registrace firem."""

    def test_notify_garants_new_org_registration_email(self, org_registration_env):
        org_user = org_registration_env["org_user"]
        garant = org_registration_env["garant"]
        EmailService.notify_garants_new_org_registration_email(org_user)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "New Co" in mail.outbox[0].subject

    def test_notify_garants_manual_registration_email(self, org_registration_env):
        profile = org_registration_env["profile"]
        garant = org_registration_env["garant"]
        EmailService.notify_garants_manual_registration_email(profile)
        assert len(mail.outbox) == 1
        assert garant.email in mail.outbox[0].to
        assert "ručně zadanými údaji" in mail.outbox[0].subject
