from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Membership
from apps.roles.models import Role
from apps.users.models import User


class CompaniesApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@smart360.local",
            password="StrongPass123",
            first_name="Owner",
        )
        Role.objects.get_or_create(
            code="company_owner",
            defaults={"label": "Company Owner"},
        )
        self.client.force_authenticate(self.user)

    def test_create_company_also_creates_membership(self):
        response = self.client.post(
            reverse("companies-list"),
            {
                "name": "Smart Company",
                "legal_name": "Smart Company LTDA",
                "slug": "smart-company",
                "status": "active",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Membership.objects.filter(user=self.user, company__slug="smart-company").exists())
