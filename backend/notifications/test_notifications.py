from datetime import date

from django.core import mail
from django.test import TestCase

from notifications.services import EmailService
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice
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
