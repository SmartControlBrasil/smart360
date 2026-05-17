from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.roles.models import Role
from apps.users.models import User


class RolesApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="roles@smart360.local",
            password="StrongPass123",
            first_name="Roles",
        )
        Role.objects.create(code="company_owner", label="Company Owner")
        self.client.force_authenticate(self.user)

    def test_list_roles(self):
        response = self.client.get(reverse("roles-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
