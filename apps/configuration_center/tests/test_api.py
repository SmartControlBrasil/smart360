from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.configuration_center.models import FeatureFlag, FeatureFlagScope, SystemSetting
from apps.users.models import User


class ConfigurationCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@smart360.local",
            password="StrongPass123!",
            first_name="SMART360",
        )
        self.company = Company.objects.create(
            name="SMART360 Industries",
            legal_name="SMART360 Industries LTDA",
            slug="smart360-industries",
            status=Company.Status.ACTIVE,
        )
        self.client.force_authenticate(self.user)

    def test_effective_settings_applies_company_override(self):
        SystemSetting.objects.create(
            key="billing.default_currency",
            group_name="billing",
            module_name="billing",
            value_type=SystemSetting.ValueType.STRING,
            value_string="BRL",
            default_value_json={"value": "BRL"},
        )
        override_url = reverse("configuration-company-override-list")
        response = self.client.post(
            override_url,
            {
                "company": self.company.id,
                "setting_key": "billing.default_currency",
                "override_value_json": {"value": "USD"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        effective_url = reverse("configuration-effective-settings")
        response = self.client.get(f"{effective_url}?module_name=billing&company={self.company.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["value"], {"value": "USD"})

    def test_effective_flags_applies_company_scope(self):
        flag = FeatureFlag.objects.create(
            key="marketplace_technicians.auto_matching_enabled",
            module_name="marketplace_technicians",
            flag_type=FeatureFlag.FlagType.BOOLEAN,
            is_enabled=False,
        )
        FeatureFlagScope.objects.create(
            feature_flag=flag,
            scope_type=FeatureFlagScope.ScopeType.COMPANY,
            company=self.company,
            is_enabled=True,
        )

        response = self.client.get(
            reverse("configuration-effective-flags"),
            {
                "module_name": "marketplace_technicians",
                "company": self.company.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["feature_flags"][0]["key"], flag.key)
        self.assertTrue(response.data["feature_flags"][0]["is_enabled"])

    def test_runtime_toggle_crud(self):
        response = self.client.post(
            reverse("configuration-runtime-toggle-list"),
            {
                "key": "disable_external_notifications",
                "module_name": "notification_center",
                "description": "Emergency operational toggle",
                "is_enabled": True,
                "notes": "Temporary disablement",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse("configuration-runtime-toggle-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
