from datetime import date

from django.db.models import Count, Q

from student_practices.models import StudentPractice, StudentPracticeWorkflowState


class DashboardService:
    @staticmethod
    def get_stats_for_user(user) -> dict:
        today = date.today()
        qs = StudentPractice.objects.filter(is_cancelled=False)

        # Department scoping if professor
        if not user.is_superuser and hasattr(user, "user_subjects"):
            dept_ids = user.user_subjects.values_list("subject__department_id", flat=True)
            if dept_ids:
                qs = qs.filter(practice__subject__department_id__in=dept_ids)

        # Aggregations by workflow_state
        state_counts = dict(qs.values("workflow_state").annotate(count=Count("student_practice_id")).values_list("workflow_state", "count"))

        formatted_counts = {}
        for state in StudentPracticeWorkflowState:
            state_key = state.name
            formatted_counts[state_key] = state_counts.get(state.value, 0)

        # Contract pending — PRELIMINARY_APPROVED without contract_received_date
        contract_pending_qs = qs.filter(
            workflow_state=StudentPracticeWorkflowState.PRELIMINARY_APPROVED.value,
            contract_received_date__isnull=True,
        ).select_related("user", "practice", "practice__employer")

        contract_pending_count = contract_pending_qs.count()

        # At risk student practices
        at_risk_qs = qs.filter(
            Q(workflow_state=StudentPracticeWorkflowState.STARTED.value, practice__end_date__lt=today)
            | Q(workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT.value, application_date__lt=today)
            | Q(workflow_state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS.value, contract_document__isnull=True)
        ).select_related("user", "practice", "practice__employer")[:50]

        at_risk_list = [
            {
                "student_practice_id": sp.student_practice_id,
                "student_name": sp.user.full_name if sp.user else "N/A",
                "practice_title": sp.practice.title if sp.practice else "N/A",
                "employer_name": sp.practice.employer.company_name if sp.practice and sp.practice.employer else "N/A",
                "workflow_state": sp.workflow_state.name if sp.workflow_state else "UNKNOWN",
                "risk_reason": (
                    "Po termínu ukončení"
                    if sp.workflow_state == StudentPracticeWorkflowState.STARTED
                    and sp.practice
                    and sp.practice.end_date
                    and sp.practice.end_date < today
                    else "Chybějící dokumenty / smlouva"
                ),
            }
            for sp in at_risk_qs
        ]

        return {
            "total_active": qs.exclude(workflow_state=StudentPracticeWorkflowState.COMPLETED.value).count(),
            "state_counts": formatted_counts,
            "contract_pending_count": contract_pending_count,
            "at_risk_count": len(at_risk_list),
            "at_risk_items": at_risk_list,
        }
