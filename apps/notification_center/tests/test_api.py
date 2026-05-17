from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.users.models import User

from ..models import InAppNotification, NotificationMessage


class NotificationCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notifications@smart360.local",
            password="StrongPass123",
            first_name="Notifications",
        )
        self.company = Company.objects.create(
            name="Notify Co",
            slug="notify-co",
            status=Company.Status.ACTIVE,
        )
        self.client.force_authenticate(self.user)

        self.channel_response = self.client.post(
            reverse("notification-channels-list"),
            {
                "name": "Email",
                "channel_type": "email",
                "description": "Transactional email channel",
                "is_active": True,
            },
            format="json",
        )
        self.channel_id = self.channel_response.data["id"]

    def test_create_template_and_message(self):
        template_response = self.client.post(
            reverse("notification-templates-list"),
            {
                "name": "Invoice Paid Email",
                "channel": self.channel_id,
                "template_key": "invoice_paid_email",
                "subject_template": "Invoice {invoice_number} paid",
                "body_template": "Hello {customer_name}, invoice {invoice_number} was paid.",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(template_response.status_code, status.HTTP_201_CREATED)

        message_response = self.client.post(
            reverse("notification-messages-list"),
            {
                "event_key": "invoice_paid",
                "channel": self.channel_id,
                "template": template_response.data["id"],
                "recipient_user": self.user.id,
                "recipient_company": self.company.id,
                "recipient_address": "finance@notify.co",
                "body_rendered": "",
                "payload": {"invoice_number": "INV-20260311-0001", "customer_name": "Notify Co"},
                "status": "pending",
            },
            format="json",
        )
        self.assertEqual(message_response.status_code, status.HTTP_201_CREATED)
        message = NotificationMessage.objects.get(id=message_response.data["id"])
        self.assertIn("INV-20260311-0001", message.body_rendered)

    def test_mark_message_delivered(self):
        message = NotificationMessage.objects.create(
            event_key="site_order_delivered",
            channel_id=self.channel_id,
            recipient_user=self.user,
            recipient_company=self.company,
            recipient_address="ops@notify.co",
            body_rendered="Site delivered",
        )
        response = self.client.post(
            reverse("notification-messages-mark-delivered", args=[message.id]),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertEqual(message.status, NotificationMessage.Status.DELIVERED)

    def test_create_and_read_in_app_notification(self):
        response = self.client.post(
            reverse("notification-in-app-notifications-list"),
            {
                "user": self.user.id,
                "title": "New Assignment",
                "body": "You have a new technician assignment.",
                "notification_type": "action_required",
                "status": "unread",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = InAppNotification.objects.get(id=response.data["id"])

        read_response = self.client.post(
            reverse("notification-in-app-notifications-mark-read", args=[notification.id]),
            {},
            format="json",
        )
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertEqual(notification.status, InAppNotification.Status.READ)

