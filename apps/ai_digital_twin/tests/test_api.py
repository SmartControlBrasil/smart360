from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class DigitalTwinApiTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)
        self.site = OperationalSiteFactory()
        self.asset = AssetFactory(operational_site=self.site)
        self.company = self.site.maintenance_client.company
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)
        self.client.force_authenticate(self.user)
        self.site_twin = DigitalTwinOrchestrator.project_for_site(site=self.site)
        self.asset_twin = DigitalTwinOrchestrator.project_for_asset(asset=self.asset)

    def test_list_twins_is_scoped_and_returns_payload(self):
        response = self.client.get(reverse("digital-twin-list"))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_get_twin_by_site(self):
        response = self.client.get(reverse("digital-twin-by-site", kwargs={"site_public_id": self.site.public_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["twin_type"], "site_operational_twin")

    def test_twin_detail_exposes_timeline_and_risk(self):
        response = self.client.get(reverse("digital-twin-detail", kwargs={"public_id": self.asset_twin.public_id}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("timeline_payload", response.data)
        risk_response = self.client.get(reverse("digital-twin-risk-profile", kwargs={"public_id": self.asset_twin.public_id}))
        self.assertEqual(risk_response.status_code, 200)
        self.assertIn("risk_level", risk_response.data)
