from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import OrganizationUser


class RefreshDeletedUserTests(TestCase):
    def test_refresh_cookie_of_deleted_user_returns_401(self):
        """F-11: refresh cookie smazaného uživatele nesmí skončit 500."""
        user = OrganizationUser.objects.create(email="gone@test.com", first_name="G", last_name="One", is_active=True)
        refresh = str(RefreshToken.for_user(user))
        user.delete()

        client = APIClient()
        client.cookies["refresh_token"] = refresh
        response = client.post("/api/users/token/refresh/")
        self.assertEqual(response.status_code, 401, response.content)


class WorkflowLabelZeroStateTests(TestCase):
    def test_practice_state_zero_has_label_not_unknown(self):
        """F-10: stav s hodnotou 0 je falsy, nesmí skončit jako „Neznámý“."""
        from practices.models import Practice, PracticeWorkflowState

        practice = Practice(workflow_state=PracticeWorkflowState.PENDING_CONTENT_APPROVAL)
        self.assertEqual(practice.workflow_status_label, "Čeká na schválení obsahu")
