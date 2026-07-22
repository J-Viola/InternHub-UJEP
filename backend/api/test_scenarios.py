"""
Test data scenario builder for E2E tests.

Each method creates a well-known database state so that Playwright tests
can rely on predictable data being present.
All methods are idempotent — they should not fail if data already exists.

TODO: CHECK FOR OTHER WAYS TO SPLIT TESTS ON DEV
"""

from datetime import date, timedelta

from django.contrib.auth.hashers import make_password

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import (
    DocumentStatus,
    DocumentType,
    StudentPractice,
    UploadedDocument,
)
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StudentUser,
    UserSubject,
    UserSubjectType,
)

# Known E2E test user credentials (must match auth.setup.js and
# TestResetDBView._create_e2e_test_users).
_E2E_STUDENT_EMAIL = "tsedlacek@example.org"
_E2E_ORGANIZATION_EMAIL = "hr@techcorp.cz"
_E2E_PROFESSOR_EMAIL = "professor@ujep.cz"


class ScenarioBuilder:
    """Build known database states for E2E test scenarios."""

    def __init__(self):
        self._pw = make_password("password123")
        self._dept = Department.objects.first()
        self._stag_st, _ = StagRole.objects.get_or_create(
            role="st",
            defaults={
                "role_name": "Student",
                "description": "Student V\u0160",
            },
        )
        self._stag_vy, _ = StagRole.objects.get_or_create(
            role="vy",
            defaults={
                "role_name": "Vyu\u010duj\u00edc\u00ed",
                "description": "Vyu\u010duj\u00edc\u00ed na kated\u0159e",
            },
        )

    # ------------------------------------------------------------------
    # Internal builders (idempotent)
    # ------------------------------------------------------------------

    def _get_or_create_student(self, email=_E2E_STUDENT_EMAIL, os_cislo="SE2E01"):
        """
        Return a StudentUser — idempotent.

        Defaults to the known E2E test student (tsedlacek@example.org).
        Falls back to creating a new student if the email doesn't exist
        (e.g. for scenario-specific additional students).
        """
        user = StudentUser.objects.filter(email=email).first()
        if user is not None:
            return user
        user, _ = StudentUser.objects.get_or_create(
            email=email,
            defaults={
                "password": self._pw,
                "first_name": "E2E",
                "last_name": "Student",
                "username": email,
                "is_active": True,
                "stag_role": self._stag_st,
                "os_cislo": os_cislo,
                "field_of_study": "Informatika",
                "year_of_study": 2,
                "skills": ["Python", "Testing"],
            },
        )
        return user

    def _get_or_create_employer(self, company="E2E Test Corp"):
        """
        Return (EmployerProfile, OrganizationUser) — idempotent.

        Defaults to the known E2E organization (hr@techcorp.cz) so that
        scenarios are visible to the storage-state user used in Playwright tests.
        Falls back to creating a new employer profile if the email doesn't exist.
        """
        org_user = OrganizationUser.objects.filter(email=_E2E_ORGANIZATION_EMAIL).first()
        if org_user is not None and hasattr(org_user, "employer_profile"):
            return org_user.employer_profile, org_user

        # Fallback: create a new employer (e.g. for scenario-specific employers).
        profile, _ = EmployerProfile.objects.get_or_create(
            ico="E2E00001",
            defaults={
                "company_name": company,
                "approval_status": ApprovalStatus.APPROVED,
                "city": "\u00dast\u00ed nad Labem",
            },
        )
        user, created = OrganizationUser.objects.get_or_create(
            email="e2e-employer@test.cz",
            defaults={
                "password": self._pw,
                "first_name": "E2E",
                "last_name": "Employer",
                "username": "e2e-employer@test.cz",
                "is_active": True,
                "employer_profile": profile,
            },
        )
        if not created and user.employer_profile_id is None:
            user.employer_profile = profile
            user.save(update_fields=["employer_profile"])
        return profile, user

    def _get_or_create_practice(self, employer_profile, title="E2E Test Practice", **kwargs):
        """Return Practice — idempotent via get_or_create."""
        defaults = {
            "title": title,
            "description": "E2E test practice description",
            "responsibilities": "Testing",
            "coefficient": 1.0,
            "employer": employer_profile,
            "start_date": date.today() + timedelta(days=30),
            "end_date": date.today() + timedelta(days=120),
            "approval_status": ApprovalStatus.APPROVED,
            "progress_status": ProgressStatus.NOT_STARTED,
            "available_positions": 2,
            "is_active": True,
        }
        defaults.update(kwargs)
        practice, _ = Practice.objects.get_or_create(
            employer=employer_profile,
            title=title,
            defaults=defaults,
        )
        return practice

    def _get_first_subject(self):
        subject = Subject.objects.first()
        if subject:
            return subject
        # Auto-create a default subject if none exists
        dept = Department.objects.first()
        subject, _ = Subject.objects.get_or_create(
            subject_code="E2E001",
            defaults={
                "subject_name": "E2E Test Subject",
                "department": dept,
            },
        )
        return subject

    # ------------------------------------------------------------------
    # Scenarios  (all idempotent thanks to get_or_create)
    # ------------------------------------------------------------------

    def student_has_applications(self):
        """Create a student with an application to an approved practice."""
        student = self._get_or_create_student()
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(profile)
        subject = self._get_first_subject()
        if subject:
            UserSubject.objects.get_or_create(
                user=student,
                subject=subject,
                defaults={"role": UserSubjectType.Student},
            )
            # Also link the E2E professor to this subject so it appears
            # in the professor's my-subjects API response.
            prof = ProfessorUser.objects.filter(email=_E2E_PROFESSOR_EMAIL).first()
            if prof:
                UserSubject.objects.get_or_create(
                    user=prof,
                    subject=subject,
                    defaults={"role": UserSubjectType.Professor},
                )
            # Link the practice to a subject so it is accessible to the
            # professor via department-based permissions.
            if practice.subject_id is None:
                practice.subject = subject
                practice.save(update_fields=["subject"])
        sp, _ = StudentPractice.objects.get_or_create(
            user=student,
            practice=practice,
            defaults={
                "school_approved": True,
                "employer_approved": True,
                "approval_status": ApprovalStatus.APPROVED,
                "progress_status": ProgressStatus.NOT_STARTED,
                "start_date": practice.start_date or date.today() + timedelta(days=30),
                "end_date": practice.end_date or date.today() + timedelta(days=120),
            },
        )
        return {
            "student_id": student.id,
            "practice_id": practice.practice_id,
            "sp_id": sp.student_practice_id,
        }

    def student_has_documents(self):
        """
        Create a student with application + PENDING documents.

        Documents are linked to the StudentPractice via the OneToOne fields
        (contract_document, content_document, feedback_document).
        """
        result = self.student_has_applications()
        sp = StudentPractice.objects.get(student_practice_id=result["sp_id"])

        doc_type_map = [
            (DocumentType.CONTRACT, "contract_document"),
            (DocumentType.CONTENT, "content_document"),
            (DocumentType.FEEDBACK, "feedback_document"),
        ]
        for doc_type, field_name in doc_type_map:
            if getattr(sp, field_name) is None:
                doc, _ = UploadedDocument.objects.get_or_create(
                    document_type=doc_type,
                    status=DocumentStatus.PENDING,
                )
                setattr(sp, field_name, doc)
                sp.save(update_fields=[field_name])
        return result

    def invitation_exists(self):
        """Create an employer with an invitation sent to a student."""
        student = self._get_or_create_student()
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(profile)

        from student_practices.services import StudentPracticeService

        StudentPracticeService.create_invitations(employer, practice.practice_id, [student.pk])
        return {"student_id": student.id, "practice_id": practice.practice_id}

    def practice_has_favorites(self):
        """Create a student with a favorited practice."""
        student = self._get_or_create_student()
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(profile)

        student.favorite_practices.add(practice)
        return {"student_id": student.id, "practice_id": practice.practice_id}

    def practice_pending_approval(self):
        """Create a practice with PENDING approval status."""
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(
            profile,
            title="E2E Pending Practice",
            approval_status=ApprovalStatus.PENDING,
        )
        # Link practice to a subject in the professor's department so it
        # appears in the department overview (see Practice.subject filter).
        subject = self._get_first_subject()
        if subject and practice.subject_id is None:
            practice.subject = subject
            practice.save(update_fields=["subject"])
        return {"practice_id": practice.practice_id}

    def application_ready(self):
        """
        Create practice + application ready for company approval.

        The student has school approval, but employer approval is still False.
        """
        student = self._get_or_create_student()
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(profile)
        subject = self._get_first_subject()
        if subject:
            UserSubject.objects.get_or_create(
                user=student,
                subject=subject,
                defaults={"role": UserSubjectType.Student},
            )
        sp, _ = StudentPractice.objects.get_or_create(
            user=student,
            practice=practice,
            defaults={
                "school_approved": True,
                "approval_status": ApprovalStatus.PENDING,
                "progress_status": ProgressStatus.NOT_STARTED,
                "start_date": practice.start_date or date.today() + timedelta(days=30),
                "end_date": practice.end_date or date.today() + timedelta(days=120),
            },
        )
        # Reset to PENDING in case a previous call already approved this SP
        if sp.approval_status != ApprovalStatus.PENDING or sp.employer_approved:
            sp.approval_status = ApprovalStatus.PENDING
            sp.employer_approved = False
            sp.school_approved = True
            sp.save(update_fields=["approval_status", "employer_approved", "school_approved"])
        return {"sp_id": sp.student_practice_id, "practice_id": practice.practice_id}

    def capacity_full(self):
        """
        Create a practice with 1 position + 1 approved student.

        The practice has available_positions=1 and one fully-approved
        StudentPractice, making it appear full.
        """
        student = self._get_or_create_student()
        student2 = self._get_or_create_student(email="e2e-student2@test.cz", os_cislo="SE2E02")
        profile, employer = self._get_or_create_employer()
        practice = self._get_or_create_practice(profile, title="E2E Capacity Full", available_positions=1)
        subject = self._get_first_subject()
        if subject:
            for s in [student, student2]:
                UserSubject.objects.get_or_create(
                    user=s,
                    subject=subject,
                    defaults={"role": UserSubjectType.Student},
                )
        StudentPractice.objects.get_or_create(
            user=student,
            practice=practice,
            defaults={
                "school_approved": True,
                "employer_approved": True,
                "approval_status": ApprovalStatus.APPROVED,
                "progress_status": ProgressStatus.NOT_STARTED,
                "start_date": practice.start_date or date.today() + timedelta(days=30),
                "end_date": practice.end_date or date.today() + timedelta(days=120),
            },
        )
        return {"practice_id": practice.practice_id}

    def dual_approval_completed(self):
        """
        Create a fully approved StudentPractice ready for document upload.

        Both school_approved and employer_approved are True,
        and approval_status is APPROVED.
        """
        result = self.student_has_applications()
        sp = StudentPractice.objects.get(student_practice_id=result["sp_id"])
        sp.school_approved = True
        sp.employer_approved = True
        sp.approval_status = ApprovalStatus.APPROVED
        sp.save(update_fields=["school_approved", "employer_approved", "approval_status"])
        return result
