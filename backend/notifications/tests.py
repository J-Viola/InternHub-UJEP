from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User

from .models import Notification, NotificationType
from .services import NotificationService


class NotificationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )

    def test_create_notification(self):
        # Clear outbox
        mail.outbox = []

        notification = NotificationService.create_notification(
            recipient=self.user,
            verb="TEST_VERB",
            message="Test zpráva",
            notification_type=NotificationType.SUCCESS,
            send_email=True,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.verb, "TEST_VERB")

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "InternHub: Test Verb")
        self.assertIn("Test zpráva", mail.outbox[0].body)

    def test_create_notification_sends_email_by_default(self):
        """Default send_email=True → e-mail je odeslán (genericky)."""
        mail.outbox = []

        notification = NotificationService.create_notification(
            recipient=self.user,
            verb="TEST_DEFAULT_EMAIL",
            message="Test s emailem",
            notification_type=NotificationType.INFO,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_create_notification_no_email_with_send_email_false(self):
        """send_email=False → žádný e-mail (jen in-app notifikace)."""
        mail.outbox = []

        notification = NotificationService.create_notification(
            recipient=self.user,
            verb="TEST_NO_EMAIL",
            message="Test bez emailu",
            notification_type=NotificationType.INFO,
            send_email=False,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)


class NotificationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="api@example.com",
            password="password123",
            first_name="API",
            last_name="User",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            first_name="Other",
            last_name="User",
        )
        self.client.force_authenticate(user=self.user)

        self.n1 = Notification.objects.create(recipient=self.user, verb="VERB1", message="Zpráva 1", is_read=False)
        self.n2 = Notification.objects.create(recipient=self.user, verb="VERB2", message="Zpráva 2", is_read=True)
        self.n_other = Notification.objects.create(recipient=self.other_user, verb="OTHER", message="Jiná zpráva")

    def test_list_notifications(self):
        url = reverse("notification-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see 2 notifications for this user
        self.assertEqual(
            len(response.data["results"] if "results" in response.data else response.data),
            2,
        )

    def test_unread_count(self):
        url = reverse("notification-unread-count")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 1)

    def test_mark_as_read(self):
        url = reverse("notification-read", args=[self.n1.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_mark_all_as_read(self):
        url = reverse("notification-read-all")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)


class NotificationMetaIndexesTest(TestCase):
    """C5.H2: Verify Notification.Meta has required indexes."""

    def test_meta_has_indexes(self):
        """C5.H2: Notification.Meta must define indexes list."""
        self.assertTrue(hasattr(Notification._meta, "indexes"), "Notification.Meta must define indexes (C5.H2)")

    def test_index_count(self):
        """C5.H2: Notification.Meta must have at least 3 indexes."""
        self.assertGreaterEqual(len(Notification._meta.indexes), 3, "Notification.Meta should have at least 3 indexes (C5.H2)")

    def test_index_names(self):
        """C5.H2: Verify expected index names exist."""
        index_names = [idx.name for idx in Notification._meta.indexes]
        expected = {
            "notificatio_recipie_2d3764_idx",  # recipient, -created_at
            "notificatio_recipie_583549_idx",  # recipient, is_read
            "notificatio_created_e4c995_idx",  # created_at
        }
        missing = expected - set(index_names)
        self.assertFalse(missing, f"Missing expected indexes: {missing}")
