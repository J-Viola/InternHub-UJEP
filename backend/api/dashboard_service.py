from datetime import date, timedelta

from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from api.models import SystemSettings
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
        approval_stall_days = SystemSettings.get_solo().practice_approval_stall_days
        credit_alert_days = SystemSettings.get_solo().practice_credit_alert_days
        approval_states = [
            StudentPracticeWorkflowState.APPLIED.value,
            StudentPracticeWorkflowState.PRELIMINARY_APPROVED.value,
            StudentPracticeWorkflowState.AWAITING_CONTENT_APPROVAL.value,
        ]
        from users.constants import ActionLogType
        from users.models import ActionLog

        ended_transition = (
            ActionLog.objects.filter(
                object_type="StudentPractice",
                object_id=OuterRef("student_practice_id"),
                action_type=ActionLogType.STATE_TRANSITION,
                action_description__contains="-> ENDED",
            )
            .order_by("-action_date")
            .values("action_date")[:1]
        )
        approval_annotations = {}
        approval_transition_filters = Q()
        approval_cutoff = timezone.now() - timedelta(days=approval_stall_days)
        for index, approval_state in enumerate(approval_states):
            state_name = StudentPracticeWorkflowState(approval_state).name
            state_transition = (
                ActionLog.objects.filter(
                    object_type="StudentPractice",
                    object_id=OuterRef("student_practice_id"),
                    action_type=ActionLogType.STATE_TRANSITION,
                    action_description__contains=f"-> {state_name}",
                )
                .order_by("-action_date")
                .values("action_date")[:1]
            )
            annotation_name = f"approval_entered_at_{index}"
            approval_annotations[annotation_name] = Coalesce(Subquery(state_transition), "updated_at")
            approval_transition_filters |= Q(workflow_state=approval_state, **{f"{annotation_name}__lt": approval_cutoff})

        now = timezone.now()
        risk_qs = (
            qs.annotate(
                ended_entered_at=Coalesce(Subquery(ended_transition), "updated_at"),
                **approval_annotations,
            )
            .filter(
                Q(workflow_state=StudentPracticeWorkflowState.STARTED.value, practice__end_date__lt=today)
                | Q(workflow_state=StudentPracticeWorkflowState.ENDED.value, ended_entered_at__lt=now - timedelta(days=credit_alert_days))
                | approval_transition_filters
                | Q(workflow_state=StudentPracticeWorkflowState.AWAITING_CONTRACT.value, application_date__lt=today)
                | Q(workflow_state=StudentPracticeWorkflowState.AWAITING_DOCUMENTS.value, contract_document__isnull=True)
            )
            .select_related("user", "practice", "practice__employer")
            .distinct()
        )
        at_risk_count = risk_qs.count()
        risk_items = []
        for sp in risk_qs.order_by("student_practice_id")[:50]:
            state = sp.workflow_state
            risk_type = None
            risk_reason = "Chybějící dokumenty / smlouva"
            if state == StudentPracticeWorkflowState.STARTED and sp.practice and sp.practice.end_date and sp.practice.end_date < today:
                risk_type, risk_reason = "OVERDUE_END", "Praxe je po plánovaném termínu ukončení."
            elif state == StudentPracticeWorkflowState.ENDED:
                if sp.ended_entered_at and sp.ended_entered_at < now - timedelta(days=credit_alert_days):
                    risk_type, risk_reason = (
                        "ENDED_NO_CREDIT",
                        (f"Praxe skončila před více než {credit_alert_days} dny bez uděleného zápočtu."),
                    )
            elif state in [StudentPracticeWorkflowState(value) for value in approval_states]:
                entered_at = getattr(sp, f"approval_entered_at_{approval_states.index(state.value)}")
                if entered_at and entered_at < timezone.now() - timedelta(days=approval_stall_days):
                    risk_type, risk_reason = "APPROVAL_STALLED", f"Praxe čeká na schválení déle než {approval_stall_days} dní."
            if risk_type:
                risk_items.append(
                    {
                        "student_practice_id": sp.student_practice_id,
                        "student_name": sp.user.full_name if sp.user else "N/A",
                        "practice_title": sp.practice.title if sp.practice else "N/A",
                        "employer_name": sp.practice.employer.company_name if sp.practice and sp.practice.employer else "N/A",
                        "workflow_state": state.name if state else "UNKNOWN",
                        "risk_type": risk_type,
                        "risk_reason": risk_reason,
                    }
                )
            elif state in (StudentPracticeWorkflowState.AWAITING_CONTRACT, StudentPracticeWorkflowState.AWAITING_DOCUMENTS):
                risk_items.append(
                    {
                        "student_practice_id": sp.student_practice_id,
                        "student_name": sp.user.full_name if sp.user else "N/A",
                        "practice_title": sp.practice.title if sp.practice else "N/A",
                        "employer_name": sp.practice.employer.company_name if sp.practice and sp.practice.employer else "N/A",
                        "workflow_state": state.name,
                        "risk_type": "MISSING_DOCUMENTS",
                        "risk_reason": risk_reason,
                    }
                )
        at_risk_list = risk_items

        return {
            "total_active": qs.exclude(workflow_state=StudentPracticeWorkflowState.COMPLETED.value).count(),
            "state_counts": formatted_counts,
            "contract_pending_count": contract_pending_count,
            "at_risk_count": at_risk_count,
            "at_risk_items": at_risk_list,
        }
