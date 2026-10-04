"""storno blokuje apply i reapply, resolve odblokuje, audit."""

from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from student_practices.services import StudentPracticeService
from subject.models import Subject
from users.constants import ActionLogType
from users.models import (
    ActionLog,
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationUser,
    ProfessorUser,
    StudentUser,
)


class CancellationResolutionTests(TestCase):
    """nevyřešené storno blokuje novou žádost; garant ho vyřeší; audit."""

    def setUp(self):
        self.client = APIClient()

        self.department = Department.objects.create(department_name="IT", department_code="IT")
        self.subject = Subject.objects.create(subject_name="Praxe", subject_code="PRX", department=self.department)

        self.student = StudentUser.objects.create(
            email="student@test.com",
            first_name="Jan",
            last_name="Student",
            is_active=True,
        )
        self.org_user = OrganizationUser.objects.create(
            email="org@test.com",
            is_active=True,
            organization_role=0,  # OWNER
        )
        self.employer_profile = EmployerProfile.objects.create(
            employer_id=self.org_user.id,
            company_name="Test Co",
            approval_status=ApprovalStatus.APPROVED,
        )
        self.org_user.employer_profile = self.employer_profile
        self.org_user.save()

        self.professor = ProfessorUser.objects.create_user(
            email="prof@test.com",
            password="password123",
            first_name="Alice",
            last_name="Prof",
            is_active=True,
            department=self.department,
            department_role=DepartmentRole.HEAD,
            is_garant_praxe=True,
        )
        self.wrong_dept = Department.objects.create(department_name="MATH", department_code="MA")
        self.wrong_dept_professor = ProfessorUser.objects.create_user(
            email="prof-math@test.com",
            password="password123",
            first_name="Cara",
            last_name="Math",
            is_active=True,
            department=self.wrong_dept,
            is_garant_praxe=True,
        )

        self.practice = Practice.objects.create(
            title="Dev Job",
            employer=self.employer_profile,
            subject=self.subject,
            contact_user=self.org_user,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            is_active=True,
            approval_status=ApprovalStatus.APPROVED,
            progress_status=ProgressStatus.NOT_STARTED,
            available_positions=5,
        )

    def _create_cancelled_sp(self):
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.CONTRACTED,
        )
        StudentPracticeService.cancel_student_practice(sp, self.student, "Zdravotní důvody")
        sp.refresh_from_db()
        return sp

    def test_cancellation_blocks_apply_and_reapply(self):
        self._create_cancelled_sp()

        # Apply blokováno (is_cancelled + cancellation_resolved_at IS NULL)
        # Poznámka: hláška apply cesty pochází z practices/services.py —
        # zde kontrolujeme jen blokaci; kanonická hláška je v reapply.
        self.client.force_authenticate(user=self.student)
        response = self.client.post("/api/practices/student/apply/", {"practice": self.practice.practice_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Reapply blokováno (dříve chybělo) s hláškou
        response = self.client.post(f"/api/student-practices/reapply/{self.practice.practice_id}/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Nelze podat novou žádost, dokud není storno vyřešeno", str(response.data))

    def test_resolve_cancellation_unblocks_apply(self):
        sp = self._create_cancelled_sp()
        self.assertIsNone(sp.cancellation_resolved_at)

        # Garant vyřeší storno
        self.client.force_authenticate(user=self.professor)
        response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/resolve-cancellation/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sp.refresh_from_db()
        self.assertIsNotNone(sp.cancellation_resolved_at)

        # Student může znovu podat žádost
        self.client.force_authenticate(user=self.student)
        response = self.client.post("/api/practices/student/apply/", {"practice": self.practice.practice_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_resolve_cancellation_permission_denied_for_foreign_department(self):
        sp = self._create_cancelled_sp()

        # Garant z jiné katedry nesmí vyřešit storno (objektová kontrola departmentu)
        self.client.force_authenticate(user=self.wrong_dept_professor)
        response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/resolve-cancellation/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        sp.refresh_from_db()
        self.assertIsNone(sp.cancellation_resolved_at)

    def test_resolve_cancellation_not_cancelled_returns_400(self):
        sp = StudentPractice.objects.create(
            user=self.student,
            practice=self.practice,
            start_date=date(2050, 1, 1),
            end_date=date(2050, 6, 1),
            approval_status=ApprovalStatus.PENDING,
            progress_status=ProgressStatus.NOT_STARTED,
            workflow_state=StudentPracticeWorkflowState.APPLIED,
        )
        self.client.force_authenticate(user=self.professor)
        response = self.client.post(f"/api/student-practices/{sp.student_practice_id}/resolve-cancellation/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancellation_action_log_contains_original_state(self):
        """ActionLog při stornu obsahuje původní název stavu."""
        sp = self._create_cancelled_sp()

        storno_logs = ActionLog.objects.filter(
            object_type="StudentPractice",
            object_id=sp.student_practice_id,
            action_type=ActionLogType.STORNO,
        )
        self.assertTrue(storno_logs.exists())
        self.assertIn("CONTRACTED", storno_logs.first().action_description)
        self.assertIn("Zdravotní důvody", storno_logs.first().action_description)
