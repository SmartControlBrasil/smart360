from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.billing.models import BillingCustomer, BillingPlan, Contract, Subscription
from apps.public_api.models import IntegrationCredential
from apps.marketplace_technicians.models import (
    ServiceRegion,
    TechnicianProfile,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
)
from apps.smart_system.models import Asset, AssetCategory, FailureEvent, MaintenanceClient, MaintenancePlan, OperationalSite, Part, ServiceOrder, StockMovement
from apps.users.models import User
from apps.identity.models import UserSession
from apps.companies.models import Membership, SiteMembership, Company


class PublicApiTests(APITestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.user = User.objects.create_user(email="public-api@smart360.local", password="StrongPass123", is_staff=True)
        self.company = Company.objects.create(name="API Company", slug="api-company")
        Membership.objects.create(user=self.user, company=self.company, status=Membership.Status.ACTIVE, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)

        self.client_entity = MaintenanceClient.objects.create(company=self.company, display_name="API Company Plant")
        self.site = OperationalSite.objects.create(maintenance_client=self.client_entity, name="Plant 01", code="PLT-01", city="Sao Paulo", state="SP")
        SiteMembership.objects.create(user=self.user, company=self.company, site=self.site, status=SiteMembership.Status.ACTIVE, is_primary=True)
        self.category = AssetCategory.objects.create(name="Compressors")
        self.asset = Asset.objects.create(operational_site=self.site, category=self.category, asset_tag="COMP-001", name="Compressor 01")
        self.plan = MaintenancePlan.objects.create(company=self.company, operational_site=self.site, asset=self.asset, name="Plano Compressor", frequency_type="monthly", frequency_value=1)
        self.order = ServiceOrder.objects.create(
            order_number="OS-API-0001",
            client=self.client_entity,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.HIGH,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="Corretiva API",
            created_by=self.user,
        )
        self.failure = FailureEvent.objects.create(asset=self.asset, service_order=self.order, symptom="Falha de partida", severity=FailureEvent.Severity.HIGH)
        self.part = Part.objects.create(company=self.company, operational_site=self.site, code="PRT-API-001", name="Sensor PT100", current_stock=8, minimum_stock=2)
        self.movement = StockMovement.objects.create(company=self.company, operational_site=self.site, part=self.part, movement_type=StockMovement.MovementType.INBOUND, quantity=5, performed_by=self.user)

        customer = BillingCustomer.objects.create(company=self.company, trade_name=self.company.name, legal_name=self.company.name, billing_email="billing@api.local")
        plan = BillingPlan.objects.create(name="Professional", slug="professional-api", billing_interval="monthly", price_amount="500.00", price_monthly="500.00")
        contract = Contract.objects.create(company=self.company, billing_customer=customer, plan=plan, billing_periodicity="monthly", contracted_amount="500.00", status="active")
        Subscription.objects.create(billing_customer=customer, company=self.company, contract=contract, plan=plan, status="active", amount="500.00")

        self.session = UserSession.objects.create(user=self.user, token_identifier="public-api-token-001", is_active=True)
        self.auth_headers = {"HTTP_AUTHORIZATION": "Bearer public-api-token-001", "HTTP_X_COMPANY_SLUG": self.company.slug, "HTTP_X_SITE_CODE": self.site.code}

        self.viewer = User.objects.create_user(email="viewer@smart360.local", password="StrongPass123", is_staff=True)
        Membership.objects.create(user=self.viewer, company=self.company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(user=self.viewer, company=self.company, site=self.site, status=SiteMembership.Status.ACTIVE, is_primary=True)
        assign_smart_system_role(self.viewer, "auditor-readonly", company=self.company)
        self.viewer_session = UserSession.objects.create(user=self.viewer, token_identifier="public-api-token-002", is_active=True)
        self.viewer_headers = {"HTTP_AUTHORIZATION": "Bearer public-api-token-002", "HTTP_X_COMPANY_SLUG": self.company.slug, "HTTP_X_SITE_CODE": self.site.code}
        self.technician_user = User.objects.create_user(email="tech-public@smart360.local", password="StrongPass123", is_staff=True)
        assign_smart_system_role(self.technician_user, "technician")
        self.technician_profile = TechnicianProfile.objects.create(
            user=self.technician_user,
            display_name="Tecnico Publico",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
            rating_average="4.70",
            completed_jobs_count=7,
        )
        self.technician_skill = TechnicianSkill.objects.create(name="chiller")
        TechnicianSkillAssignment.objects.create(
            technician_profile=self.technician_profile,
            skill=self.technician_skill,
        )
        self.technician_region = ServiceRegion.objects.create(
            name="Capital SP",
            state="SP",
            city="Sao Paulo",
        )
        TechnicianServiceRegion.objects.create(
            technician_profile=self.technician_profile,
            service_region=self.technician_region,
        )
        self.technician_session = UserSession.objects.create(
            user=self.technician_user,
            token_identifier="public-api-token-003",
            is_active=True,
        )
        self.technician_headers = {"HTTP_AUTHORIZATION": "Bearer public-api-token-003"}

    def test_context_endpoint_requires_authentication(self):
        response = self.client.get(reverse("public-api:public-context"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_context_endpoint_returns_scope(self):
        response = self.client.get(reverse("public-api:public-context"), **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["active_company"]["slug"], self.company.slug)
        self.assertEqual(response.data["active_site"]["code"], self.site.code)

    def test_assets_endpoint_is_scoped(self):
        other_company = Company.objects.create(name="Other Company", slug="other-company")
        other_client = MaintenanceClient.objects.create(company=other_company, display_name="Other")
        other_site = OperationalSite.objects.create(maintenance_client=other_client, name="Other Site", code="OTH-01")
        other_asset = Asset.objects.create(operational_site=other_site, category=self.category, asset_tag="COMP-999", name="Restricted")

        response = self.client.get(reverse("public-api:public-assets-list"), **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags = {item["asset_tag"] for item in response.data["results"]}
        self.assertIn(self.asset.asset_tag, tags)
        self.assertNotIn(other_asset.asset_tag, tags)

    def test_can_create_work_order_with_token_auth(self):
        response = self.client.post(
            reverse("public-api:public-work-orders-list"),
            {
                "client_id": str(self.client_entity.public_id),
                "operational_site_id": str(self.site.public_id),
                "asset_id": str(self.asset.public_id),
                "maintenance_type": "corrective",
                "priority": "high",
                "status": "open",
                "source": "manual",
                "title": "Nova OS via API",
                "description": "Criada por integracao",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["order_number"].startswith("OS-"))

    def test_readonly_role_cannot_create_work_order(self):
        response = self.client.post(
            reverse("public-api:public-work-orders-list"),
            {
                "client_id": str(self.client_entity.public_id),
                "operational_site_id": str(self.site.public_id),
                "asset_id": str(self.asset.public_id),
                "maintenance_type": "corrective",
                "priority": "high",
                "status": "open",
                "source": "manual",
                "title": "OS negada",
                "description": "Nao deveria criar",
            },
            format="json",
            **self.viewer_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_download_respects_scope(self):
        response = self.client.get(
            reverse("public-api:public-report-download", kwargs={"report_type": "work-order", "reference_code": self.order.public_id}),
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_suspended_tenant_is_blocked(self):
        subscription = Subscription.objects.filter(company=self.company).first()
        subscription.status = Subscription.Status.SUSPENDED
        subscription.save(update_fields=["status", "updated_at"])

        response = self.client.get(reverse("public-api:public-assets-list"), **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_integration_credential_authentication_works(self):
        credential = IntegrationCredential(name="ERP Sync", user=self.user, company=self.company, created_by=self.user)
        raw_token = credential.issue_token()
        credential.save()

        response = self.client.get(
            reverse("public-api:public-context"),
            HTTP_AUTHORIZATION=f"ApiKey {raw_token}",
            HTTP_X_COMPANY_SLUG=self.company.slug,
            HTTP_X_SITE_CODE=self.site.code,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authentication_mode"], "integration")

    def test_integration_credential_scope_blocks_forbidden_action(self):
        credential = IntegrationCredential(name="Readonly ERP", user=self.user, company=self.company, created_by=self.user, allowed_scopes=["assets.view"])
        raw_token = credential.issue_token()
        credential.save()

        response = self.client.post(
            reverse("public-api:public-work-orders-list"),
            {
                "client_id": str(self.client_entity.public_id),
                "operational_site_id": str(self.site.public_id),
                "asset_id": str(self.asset.public_id),
                "maintenance_type": "corrective",
                "priority": "high",
                "status": "open",
                "source": "manual",
                "title": "OS bloqueada por escopo",
                "description": "Integracao sem escopo para criar OS",
            },
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {raw_token}",
            HTTP_X_COMPANY_SLUG=self.company.slug,
            HTTP_X_SITE_CODE=self.site.code,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_requested_company_outside_scope_is_denied(self):
        other_company = Company.objects.create(name="Forbidden Company", slug="forbidden-company")
        response = self.client.get(
            reverse("public-api:public-context"),
            HTTP_AUTHORIZATION="Bearer public-api-token-001",
            HTTP_X_COMPANY_SLUG=other_company.slug,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assets_support_filtering_and_pagination(self):
        Asset.objects.create(operational_site=self.site, category=self.category, asset_tag="COMP-002", name="Compressor 02", status=Asset.Status.STOPPED)
        response = self.client.get(
            reverse("public-api:public-assets-list"),
            {"status": Asset.Status.STOPPED, "page_size": 1},
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_public_schema_endpoint_is_available(self):
        response = self.client.get(reverse("public-api-schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_marketplace_request_creation(self):
        response = self.client.post(
            reverse("public-api:public-marketplace-service-requests-list"),
            {
                "title": "Atendimento em campo para chiller",
                "description": "Cliente precisa de tecnico para diagnostico no local.",
                "category": "chiller",
                "service_type": "maintenance",
                "priority": "high",
                "city": "Sao Paulo",
                "state": "SP",
                "location_label": "Sala tecnica",
                "requester_company_id": str(self.company.public_id),
                "related_site_id": str(self.site.public_id),
                "related_asset_id": str(self.asset.public_id),
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company_name"], self.company.name)

    def test_public_marketplace_offer_flow(self):
        service_request = TechnicianServiceRequest.objects.create(
            requester_user=self.user,
            requester_company=self.company,
            title="Falha em esteira",
            description="Solicitacao para tecnico externo",
            category="esteira",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.OPEN,
        )

        offer_response = self.client.post(
            reverse("public-api:public-marketplace-offers-list"),
            {
                "service_request_id": str(service_request.public_id),
                "technician_profile_id": str(self.technician_profile.public_id),
                "proposed_amount": "420.00",
                "message": "Atendo hoje no periodo da tarde.",
                "estimated_hours": 4,
            },
            format="json",
            **self.technician_headers,
        )
        self.assertEqual(offer_response.status_code, status.HTTP_201_CREATED)

        accept_response = self.client.post(
            reverse(
                "public-api:public-marketplace-offers-accept",
                kwargs={"public_id": offer_response.data["public_id"]},
            ),
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertEqual(accept_response.data["assignment_status"], "assigned")

        start_response = self.client.post(
            reverse(
                "public-api:public-marketplace-assignments-start",
                kwargs={"public_id": accept_response.data["public_id"]},
            ),
            format="json",
            **self.technician_headers,
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

    def test_public_marketplace_matching_endpoint_returns_breakdown(self):
        service_request = TechnicianServiceRequest.objects.create(
            requester_user=self.user,
            requester_company=self.company,
            title="Atendimento em campo para chiller",
            description="Solicitacao para matching",
            category="chiller",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.OPEN,
        )

        response = self.client.post(
            reverse(
                "public-api:public-marketplace-service-requests-matching",
                kwargs={"public_id": service_request.public_id},
            ),
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn("match_score", response.data[0])
        self.assertIn("score_specialty", response.data[0])
