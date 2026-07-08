"""
CRITICAL REGRESSION TESTS — State Machine Permissions (CR-1, CR-3).

Purpose:
  These tests verify that only authorized users can transition/cancel Practice
  and StudentPractice entities. FAILING tests indicate a security vulnerability
  (object permission bypass).

CR-1: Only stag teachers, garant praxe, and admins can transition practices.
      Students and unauthorized users must be blocked.

CR-3: Teachers from other departments must NOT be able to transition practices
      outside their department scope.

NOTE on test_teacher_from_other_department_cannot_transition:
  This test may FAIL initially if CR-3 department-level permission guards are
  not yet implemented. The test asserts expected CORRECT behavior (403).
  Fix the missing permission guard in permissions.py to make it pass.

Related: C8.5 (healthcheck), conftest.org_user fix (C8.1).
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from department.models import Department
from practices.models import PracticeWorkflowState
from users.models import ProfessorUser

# ---------------------------------------------------------------------------
# Fixtures for CR-1 / CR-3 tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """DRF API test client (unauthenticated by default)."""
    return APIClient()


@pytest.fixture
def garant_user(db, department):
    """ProfessorUser with is_garant_praxe=True — should pass all transition gates."""
    garant = ProfessorUser.objects.create(
        email="garant@test.com",
        first_name="Garant",
        last_name="Praxe",
        is_active=True,
        is_garant_praxe=True,
        department=department,
    )
    return garant


@pytest.fixture
def other_department(db):
    """Another department to test cross-department access restrictions."""
    return Department.objects.create(
        department_name="Fyzika",
        department_code="FY",
    )


@pytest.fixture
def other_dept_teacher(db, other_department):
    """ProfessorUser from a DIFFERENT department than the practice's subject."""
    teacher = ProfessorUser.objects.create(
        email="otherdept@test.com",
        first_name="Other",
        last_name="Teacher",
        is_active=True,
        is_garant_praxe=False,
        department=other_department,
    )
    return teacher


@pytest.fixture
def cancelled_practice(db, practice):
    """A practice that has been cancelled — IsNotCancelled guard must block mutations."""
    practice.is_cancelled = True
    practice.save(update_fields=["is_cancelled"])
    return practice


# ---------------------------------------------------------------------------
# CR-1: Student cannot transition/cancel practices
# ---------------------------------------------------------------------------


class TestStudentCannotMutatePractice:
    """
    CR-1 regression: students must NOT be able to transition or cancel practices.

    TransitionPracticeView requires: IsStagTeacher | IsGarantPraxe | IsAdminUser
    CancelPracticeView requires: CanCancelPractice (admin, dept head, garant)

    A StudentUser satisfies NONE of these → must get 403.
    """

    def test_student_cannot_transition_practice(self, client, student_user, practice):
        """
        CR-1: Student (not teacher/admin) cannot transition a practice.
        The TransitionPracticeView permission classes do not include students.
        """
        client.force_authenticate(user=student_user)
        response = client.post(
            f"/api/practices/{practice.pk}/transition/",
            {"target_state": PracticeWorkflowState.CONTENT_APPROVED.value},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"CR-1 VULNERABILITY: Student got {response.status_code} instead of 403. "
            f"StudentUser must NOT be able to transition practices."
        )

    def test_student_cannot_cancel_practice(self, client, student_user, practice):
        """
        CR-1: Student cannot cancel a practice.
        CancelPracticeView requires CanCancelPractice, which excludes students.
        """
        client.force_authenticate(user=student_user)
        response = client.post(
            f"/api/practices/{practice.pk}/cancel/",
            {"reason": "test"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"CR-1 VULNERABILITY: Student got {response.status_code} instead of 403. " f"StudentUser must NOT be able to cancel practices."
        )


# ---------------------------------------------------------------------------
# CR-3: Cross-department teacher restriction
# ---------------------------------------------------------------------------


class TestCrossDepartmentRestriction:
    """
    CR-3 regression: teachers from other departments must NOT be able to
    transition practices belonging to a different department.

    NOTE: If CR-3 guard is not yet implemented in permissions.py, these tests
    will FAIL (they correctly assert 403). This is the desired behavior of a
    regression test — it detects the missing permission check.
    """

    def test_teacher_from_other_department_cannot_transition(self, client, other_dept_teacher, practice):
        """
        CR-3: Teacher from another department cannot transition a practice
        whose subject belongs to a different department.

        Current state: IsStagTeacher only checks isinstance(ProfessorUser)
        without department scope. This test will FAIL until a department-level
        check is added to TransitionPracticeView permissions.
        """
        # Ensure the practice's subject is in a different department
        # than the other_dept_teacher's department.
        from subject.models import Subject

        teacher_dept = other_dept_teacher.department
        practice_subject = Subject.objects.create(
            subject_name="Test Subject",
            department=Department.objects.create(department_name="Chemie", department_code="CH"),
        )
        practice.subject = practice_subject
        practice.save(update_fields=["subject"])

        client.force_authenticate(user=other_dept_teacher)
        response = client.post(
            f"/api/practices/{practice.pk}/transition/",
            {"target_state": PracticeWorkflowState.CONTENT_APPROVED.value},
            format="json",
        )
        # WARNING: This assertion will FAIL if CR-3 guard is missing.
        # Fix: add department-level check to IsStagTeacher or a new permission class.
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"CR-3 VULNERABILITY: Other-dept teacher got {response.status_code} instead of 403. "
            f"A teacher from department '{teacher_dept}' must NOT be able to transition "
            f"a practice in department '{practice_subject.department}'."
        )


# ---------------------------------------------------------------------------
# Positive test: Garant can transition
# ---------------------------------------------------------------------------


class TestGarantCanTransition:
    """Garant praxe (is_garant_praxe=True) can transition practices."""

    def test_garant_praxe_can_transition(self, client, garant_user, practice):
        """Positive test: Garant praxe satisfies IsGarantPraxe permission."""
        client.force_authenticate(user=garant_user)
        response = client.post(
            f"/api/practices/{practice.pk}/transition/",
            {"target_state": PracticeWorkflowState.CONTENT_APPROVED.value},
            format="json",
        )
        # Garant should NOT get 403; valid transitions may return 200 (success)
        # or 400 (invalid transition logic), but never 403.
        assert response.status_code != status.HTTP_403_FORBIDDEN, (
            "Garant got 403 — should be allowed to transition. " "Check is_garant_praxe flag and IsGarantPraxe permission class."
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ], f"Unexpected status {response.status_code} for garant transition."


# ---------------------------------------------------------------------------
# IsNotCancelled guard test
# ---------------------------------------------------------------------------


class TestIsNotCancelledGuard:
    """
    WP3.1: IsNotCancelled guard must block all mutations on cancelled entities.
    """

    def test_is_not_cancelled_blocks_transition(self, client, professor_user, cancelled_practice):
        """
        IsNotCancelled must block transition of a cancelled practice,
        returning 403 regardless of the user's role.
        """
        client.force_authenticate(user=professor_user)
        response = client.post(
            f"/api/practices/{cancelled_practice.pk}/transition/",
            {"target_state": PracticeWorkflowState.CONTENT_APPROVED.value},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"IsNotCancelled guard failure: got {response.status_code} instead of 403. " f"Cancelled practices must be immutable."
        )

    def test_is_not_cancelled_blocks_cancel(self, client, professor_user, cancelled_practice):
        """IsNotCancelled must also block cancel on already cancelled practice."""
        client.force_authenticate(user=professor_user)
        response = client.post(
            f"/api/practices/{cancelled_practice.pk}/cancel/",
            {"reason": "double cancel test"},
            format="json",
        )
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"IsNotCancelled guard failure on cancel: got {response.status_code} instead of 403."
