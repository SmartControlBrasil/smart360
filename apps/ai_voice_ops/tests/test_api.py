from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_voice_ops.models import VoiceInteraction
from tests.factories.core import MembershipFactory, SiteMembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, MaintenanceClientFactory, OperationalSiteFactory, ServiceOrderFactory


class VoiceOpsApiTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)
        self.client_obj = MaintenanceClientFactory()
        self.company = self.client_obj.company
        self.site = OperationalSiteFactory(maintenance_client=self.client_obj)
        self.asset = AssetFactory(operational_site=self.site)
        self.order = ServiceOrderFactory(
            client=self.client_obj,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            status="open",
            order_number="OS-2026-2101",
        )
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        SiteMembershipFactory(user=self.user, company=self.company, site=self.site, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)
        self.client.force_authenticate(self.user)

    def test_process_endpoint_executes_technician_action(self):
        response = self.client.post(
            reverse("voiceops-process"),
            {
                "persona": "technician",
                "channel": "pwa",
                "transcript_text": "iniciar ordem de servico OS-2026-2101",
                "audio_metadata": {"provider": "browser"},
                "context_seed": {
                    "order_code": self.order.order_number,
                    "company_id": self.company.id,
                    "site_id": self.site.id,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["action"]["status"], "executed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "in_progress")

    def test_catalog_endpoint_lists_supported_personas(self):
        response = self.client.get(reverse("voiceops-catalog"))
        self.assertEqual(response.status_code, 200)
        personas = {item["persona"] for item in response.data}
        self.assertEqual(personas, {"technician", "manager", "client"})

    def test_process_endpoint_supports_manager_voice_query(self):
        response = self.client.post(
            reverse("voiceops-process"),
            {
                "persona": "manager",
                "channel": "desktop",
                "transcript_text": "resuma a operacao",
                "audio_metadata": {"provider": "browser"},
                "context_seed": {"company_id": self.company.id, "site_id": self.site.id},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["action"]["status"], "response_only")
        self.assertIn("summary", response.data["response"])

    def test_interactions_endpoint_is_scoped(self):
        VoiceInteraction.objects.create(
            user=self.user,
            company=self.company,
            site=self.site,
            persona="manager",
            channel="desktop",
            transcript_status="transcribed",
            transcript_text="resuma a operacao",
            detected_intent="query_summary",
            action_status="response_only",
            response_payload={"summary": "Resumo pronto."},
        )
        response = self.client.get(reverse("voiceops-interaction-list"), {"company": self.company.id})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)
