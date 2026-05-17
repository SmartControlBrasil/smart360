from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_voice_ops.models import VoiceInteraction
from apps.ai_voice_ops.services.intents import VoiceIntentService
from apps.ai_voice_ops.services.orchestrator import VoiceOpsOrchestrator
from apps.ai_voice_ops.services.transcription import VoiceTranscriptionService
from apps.observability_center.models import SystemEventLog
from tests.factories.core import MembershipFactory, SiteMembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, MaintenanceClientFactory, OperationalSiteFactory, ServiceOrderFactory


class VoiceOpsServiceTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.factory = RequestFactory()
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
            order_number="OS-2026-1101",
        )
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        SiteMembershipFactory(user=self.user, company=self.company, site=self.site, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)

    def _request(self):
        request = self.factory.post("/api/v1/ai-voiceops/process/")
        request.user = self.user
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session["smart_system_active_company_id"] = self.company.id
        request.session["smart_system_active_site_id"] = self.site.id
        request.session.save()
        return request

    def test_transcription_cleans_noise_and_keeps_text(self):
        payload = VoiceTranscriptionService.transcribe(
            transcript_text="[noise] iniciar ordem de servico OS-2026-1101",
            audio_metadata={"provider": "browser"},
        )
        self.assertEqual(payload["status"], "transcribed")
        self.assertIn("iniciar ordem de servico", payload["transcript_text"])

    def test_intent_parser_detects_technician_start_intent(self):
        parsed = VoiceIntentService.parse(
            persona="technician",
            transcript_text="iniciar ordem de servico OS-2026-1101",
        )
        self.assertEqual(parsed.key, "start_work_order")
        self.assertEqual(parsed.entities["order_code"], "OS-2026-1101")

    def test_orchestrator_executes_safe_technician_command(self):
        payload = VoiceOpsOrchestrator.process(
            request=self._request(),
            persona="technician",
            channel="pwa",
            transcript_text="iniciar ordem de servico OS-2026-1101",
            audio_metadata={"provider": "browser"},
            context_seed={"order_code": self.order.order_number, "company_id": self.company.id, "site_id": self.site.id},
        )
        self.order.refresh_from_db()
        self.assertEqual(payload["action"]["status"], "executed")
        self.assertEqual(self.order.status, "in_progress")
        self.assertTrue(VoiceInteraction.objects.filter(persona="technician", detected_intent="start_work_order").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="voice.action.executed").exists())

    def test_orchestrator_blocks_completion_without_required_signatures(self):
        payload = VoiceOpsOrchestrator.process(
            request=self._request(),
            persona="technician",
            channel="pwa",
            transcript_text="finalizar os OS-2026-1101",
            audio_metadata={"provider": "browser"},
            context_seed={"order_code": self.order.order_number, "company_id": self.company.id, "site_id": self.site.id},
        )
        self.assertEqual(payload["action"]["status"], "blocked")
