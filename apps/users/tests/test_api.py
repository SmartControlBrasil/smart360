from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User


class UsersApiTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            email="admin@smart360.local",
            password=self.password,
            first_name="Admin",
            last_name="User",
        )

    def test_login_returns_token_and_user(self):
        response = self.client.post(
            reverse("users-login"),
            {"email": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)
