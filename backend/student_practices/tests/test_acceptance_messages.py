"""
Hlášky předepsané v Tests/UAT/UATs.xlsx: povinný důvod zamítnutí (TC-06-03) a formát uploadu (TC-04-02).
"""

from django.test import SimpleTestCase

from practices.models import PracticeWorkflowState
from practices.serializers import TransitionPracticeSerializer
from student_practices.models import StudentPracticeWorkflowState
from student_practices.serializers import TransitionStudentPracticeSerializer


class RejectionReasonRequiredTests(SimpleTestCase):
    def test_student_practice_rejection_requires_reason(self):
        for state in (
            StudentPracticeWorkflowState.REJECTED,
            StudentPracticeWorkflowState.CONTENT_REJECTED,
            StudentPracticeWorkflowState.DOCUMENTS_REJECTED,
        ):
            with self.subTest(state=state.name):
                for reason in (None, "", "   "):
                    data = {"target_state": state.value}
                    if reason is not None:
                        data["reason"] = reason
                    serializer = TransitionStudentPracticeSerializer(data=data)
                    self.assertFalse(serializer.is_valid())
                    self.assertEqual(str(serializer.errors["reason"][0]), "Důvod zamítnutí je povinný.")

    def test_student_practice_rejection_with_reason_is_valid(self):
        serializer = TransitionStudentPracticeSerializer(
            data={"target_state": StudentPracticeWorkflowState.REJECTED.value, "reason": "Nevhodná náplň praxe"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_non_rejecting_transition_needs_no_reason(self):
        serializer = TransitionStudentPracticeSerializer(data={"target_state": StudentPracticeWorkflowState.PRELIMINARY_APPROVED.value})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_practice_content_rejection_requires_reason(self):
        serializer = TransitionPracticeSerializer(data={"target_state": PracticeWorkflowState.CONTENT_REJECTED.value})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors["reason"][0]), "Důvod zamítnutí je povinný.")

    def test_practice_approval_needs_no_reason(self):
        serializer = TransitionPracticeSerializer(data={"target_state": PracticeWorkflowState.CONTENT_APPROVED.value})
        self.assertTrue(serializer.is_valid(), serializer.errors)
