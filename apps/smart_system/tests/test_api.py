from datetime import timedelta

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, Membership, SiteMembership
from apps.users.models import User

from ..models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    ContractAsset,
    MaintenanceContract,
    MaintenanceClient,
    OperationalSite,
    QuoteItem,
    RoutePlan,
    ScheduledVisit,
    ServiceQuote,
    ServiceOrder,
    ServiceSignature,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
    WorkLog,
)


class SmartSystemApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="maintenance@smart360.local",
            password="StrongPass123",
            first_name="Maintenance",
        )
        self.client.force_authenticate(self.user)
        self.company = Company.objects.create(name="Industria Alfa", slug="industria-alfa")
        self.maintenance_client = MaintenanceClient.objects.create(display_name="Industria Alfa", company=self.company)
        self.site = OperationalSite.objects.create(maintenance_client=self.maintenance_client, name="Unidade 01", city="Sao Paulo", state="SP")
        Membership.objects.create(user=self.user, company=self.maintenance_client.company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(
            user=self.user,
            company=self.maintenance_client.company,
            site=self.site,
            status=SiteMembership.Status.ACTIVE,
            is_primary=True,
        )
        self.category = AssetCategory.objects.create(name="Motores")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="MTR-001",
            name="Motor Principal",
        )
        self.other_company = Company.objects.create(name="Industria Beta", slug="industria-beta")
        self.other_client = MaintenanceClient.objects.create(display_name="Industria Beta", company=self.other_company)
        self.other_site = OperationalSite.objects.create(
            maintenance_client=self.other_client,
            name="Unidade 02",
            city="Campinas",
            state="SP",
        )
        self.other_asset = Asset.objects.create(
            operational_site=self.other_site,
            category=self.category,
            asset_tag="MTR-999",
            name="Motor Restrito",
        )

    def test_create_maintenance_contract_with_asset_scope(self):
        response = self.client.post(
            reverse("smart-system-maintenance-contracts-list"),
            {
                "company": self.company.id,
                "client": self.maintenance_client.id,
                "operational_site": self.site.id,
                "start_date": timezone.localdate().isoformat(),
                "status": "draft",
                "billing_frequency": "monthly",
                "contract_value": "1500.00",
                "covered_assets": [
                    {
                        "asset": self.asset.id,
                        "maintenance_frequency": "monthly",
                        "maintenance_frequency_days": 30,
                        "estimated_duration_minutes": 120,
                        "next_execution": timezone.localdate().isoformat(),
                        "is_active": True,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        contract = MaintenanceContract.objects.get(company=self.company)
        self.assertTrue(contract.contract_number.startswith("MCT-"))
        self.assertEqual(contract.covered_assets.count(), 1)

    def test_generate_preventives_from_active_contract(self):
        contract = MaintenanceContract.objects.create(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-202603-0001",
            start_date=timezone.localdate(),
            status=MaintenanceContract.Status.ACTIVE,
            billing_frequency=MaintenanceContract.BillingFrequency.MONTHLY,
            contract_value="1200.00",
            next_billing_date=timezone.localdate(),
        )
        ContractAsset.objects.create(
            contract=contract,
            asset=self.asset,
            maintenance_frequency=ContractAsset.MaintenanceFrequency.MONTHLY,
            maintenance_frequency_days=30,
            estimated_duration_minutes=90,
            next_execution=timezone.localdate(),
        )

        response = self.client.post(
            reverse("smart-system-maintenance-contracts-generate-preventives", kwargs={"pk": contract.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ServiceOrder.objects.filter(
                maintenance_contract=contract,
                contract_asset__asset=self.asset,
                maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE,
            ).exists()
        )

    def test_generate_billing_cycle_for_contract(self):
        contract = MaintenanceContract.objects.create(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-202603-0002",
            start_date=timezone.localdate(),
            status=MaintenanceContract.Status.ACTIVE,
            billing_frequency=MaintenanceContract.BillingFrequency.MONTHLY,
            contract_value="950.00",
            next_billing_date=timezone.localdate(),
        )

        response = self.client.post(
            reverse("smart-system-maintenance-contracts-generate-billing", kwargs={"pk": contract.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contract.refresh_from_db()
        self.assertNotEqual(response.data["invoice_number"], "")
        self.assertGreater(contract.next_billing_date, timezone.localdate())

    def test_create_service_order_generates_order_number_and_history(self):
        response = self.client.post(
            reverse("smart-system-service-orders-list"),
            {
                "client": self.maintenance_client.id,
                "operational_site": self.site.id,
                "asset": self.asset.id,
                "maintenance_type": "corrective",
                "priority": "high",
                "status": "open",
                "source": "manual",
                "title": "Motor com ruído anormal",
                "description": "Verificar vibração e ruído",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["order_number"].startswith("SS-"))
        self.assertTrue(
            AssetHistoryEvent.objects.filter(
                asset=self.asset,
                event_type=AssetHistoryEvent.EventType.SERVICE_ORDER_CREATED,
            ).exists()
        )

    def test_complete_service_order_creates_completion_history(self):
        service_order = ServiceOrder.objects.create(
            order_number="SS-TEST-0001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE,
            priority=ServiceOrder.Priority.MEDIUM,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="Inspecao preventiva",
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("smart-system-service-orders-detail", kwargs={"pk": service_order.pk}),
            {"status": "completed", "final_observations": "Execucao concluida com sucesso"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AssetHistoryEvent.objects.filter(
                asset=self.asset,
                event_type=AssetHistoryEvent.EventType.SERVICE_ORDER_COMPLETED,
            ).exists()
        )

    def test_create_failure_event_generates_asset_history(self):
        response = self.client.post(
            reverse("smart-system-failure-events-list"),
            {
                "asset": self.asset.id,
                "symptom": "Parada repentina",
                "severity": "critical",
                "status": "open",
                "downtime_minutes": 45,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AssetHistoryEvent.objects.filter(
                asset=self.asset,
                event_type=AssetHistoryEvent.EventType.FAILURE_REPORTED,
            ).exists()
        )

    def test_work_log_calculates_labor_minutes(self):
        service_order = ServiceOrder.objects.create(
            order_number="SS-TEST-0002",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.INSPECTION,
            priority=ServiceOrder.Priority.LOW,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="Inspecao",
            created_by=self.user,
        )
        start = timezone.now()
        end = start + timedelta(minutes=90)

        response = self.client.post(
            reverse("smart-system-work-logs-list"),
            {
                "service_order": service_order.id,
                "user": self.user.id,
                "started_at": start.isoformat(),
                "ended_at": end.isoformat(),
                "notes": "Atendimento executado",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        work_log = WorkLog.objects.get(service_order=service_order)
        self.assertEqual(work_log.labor_minutes, 90)

    def test_list_assets_is_scoped_to_membership_company_and_site(self):
        response = self.client.get(reverse("smart-system-assets-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_tags = {item["asset_tag"] for item in response.data}
        self.assertIn(self.asset.asset_tag, returned_tags)
        self.assertNotIn(self.other_asset.asset_tag, returned_tags)

    def test_direct_access_to_foreign_asset_is_denied_by_scope(self):
        response = self.client.get(reverse("smart-system-assets-detail", kwargs={"pk": self.other_asset.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_service_order_with_foreign_scope_reference_is_rejected(self):
        response = self.client.post(
            reverse("smart-system-service-orders-list"),
            {
                "client": self.other_client.id,
                "operational_site": self.other_site.id,
                "asset": self.other_asset.id,
                "maintenance_type": "corrective",
                "priority": "high",
                "status": "open",
                "source": "manual",
                "title": "Tentativa fora do escopo",
                "description": "Nao deveria passar",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_service_signature_list_is_scoped_to_company_and_site(self):
        local_order = ServiceOrder.objects.create(
            order_number="SS-SIGN-001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.MEDIUM,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="OS local",
            created_by=self.user,
        )
        foreign_order = ServiceOrder.objects.create(
            order_number="SS-SIGN-999",
            client=self.other_client,
            operational_site=self.other_site,
            asset=self.other_asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.MEDIUM,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="OS externa",
            created_by=self.user,
        )
        ServiceSignature.objects.create(
            signature_type=ServiceSignature.SignatureType.TECHNICIAN_COMPLETION,
            signer_role=ServiceSignature.SignerRole.TECHNICIAN,
            signer_name="Tecnico Local",
            signer_user=self.user,
            company=self.maintenance_client.company,
            operational_site=self.site,
            service_order=local_order,
            signature_data="data:image/png;base64,AAAA",
        )
        ServiceSignature.objects.create(
            signature_type=ServiceSignature.SignatureType.CLIENT_ACCEPTANCE,
            signer_role=ServiceSignature.SignerRole.CLIENT_RESPONSIBLE,
            signer_name="Cliente Externo",
            company=self.other_company,
            operational_site=self.other_site,
            service_order=foreign_order,
            signature_data="data:image/png;base64,BBBB",
        )

        response = self.client.get(reverse("smart-system-service-signatures-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_scheduled_visit_and_list_by_technician(self):
        visit = ScheduledVisit.objects.create(
            company=self.maintenance_client.company,
            operational_site=self.site,
            asset=self.asset,
            work_order=ServiceOrder.objects.create(
                order_number="SS-SCH-001",
                client=self.maintenance_client,
                operational_site=self.site,
                asset=self.asset,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
                priority=ServiceOrder.Priority.HIGH,
                status=ServiceOrder.Status.SCHEDULED,
                source=ServiceOrder.Source.MANUAL,
                title="OS agenda",
                assigned_to=self.user,
                created_by=self.user,
            ),
            technician=self.user,
            source_type=ScheduledVisit.SourceType.WORK_ORDER,
            title="Visita OS agenda",
            scheduled_date=timezone.localdate(),
            priority=ScheduledVisit.Priority.HIGH,
            status=ScheduledVisit.Status.SCHEDULED,
        )

        response = self.client.get(
            reverse("smart-system-scheduled-visits-by-technician"),
            {"technician": self.user.id, "date": timezone.localdate().isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["public_id"], str(visit.public_id))

    def test_generate_route_plan_for_technician(self):
        TechnicianAvailabilityWindow.objects.create(
            company=self.maintenance_client.company,
            operational_site=self.site,
            technician=self.user,
            weekday=timezone.localdate().isoweekday(),
            start_time=timezone.datetime.strptime("08:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("18:00", "%H:%M").time(),
            is_available=True,
        )
        order = ServiceOrder.objects.create(
            order_number="SS-SCH-002",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.HIGH,
            status=ServiceOrder.Status.SCHEDULED,
            source=ServiceOrder.Source.MANUAL,
            title="OS com rota",
            assigned_to=self.user,
            created_by=self.user,
            scheduled_start=timezone.now(),
        )
        ScheduledVisit.objects.create(
            company=self.maintenance_client.company,
            operational_site=self.site,
            asset=self.asset,
            work_order=order,
            technician=self.user,
            source_type=ScheduledVisit.SourceType.WORK_ORDER,
            title="Visita com rota",
            scheduled_date=timezone.localdate(),
            priority=ScheduledVisit.Priority.HIGH,
            status=ScheduledVisit.Status.SCHEDULED,
        )

        response = self.client.post(
            reverse("smart-system-route-plans-list"),
            {"technician": self.user.id, "date": timezone.localdate().isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RoutePlan.objects.filter(company=self.maintenance_client.company, technician=self.user).exists())
        self.assertTrue(TechnicianSchedule.objects.filter(company=self.maintenance_client.company, technician=self.user).exists())

    def test_create_service_quote_calculates_totals(self):
        order = ServiceOrder.objects.create(
            order_number="SS-QTE-001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.HIGH,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="OS com orcamento",
            created_by=self.user,
        )

        response = self.client.post(
            reverse("smart-system-service-quotes-list"),
            {
                "company": self.maintenance_client.company.id,
                "operational_site": self.site.id,
                "work_order": order.id,
                "asset": self.asset.id,
                "notes": "Orcamento tecnico inicial",
                "items": [
                    {
                        "item_type": "part",
                        "description": "Sensor PT100",
                        "part_reference": "PRT-0001",
                        "quantity": "2.00",
                        "unit_price": "120.00",
                    },
                    {
                        "item_type": "labor",
                        "description": "Mao de obra tecnica",
                        "estimated_minutes": 120,
                        "hourly_rate": "180.00",
                        "quantity": "2.00",
                        "unit_price": "180.00",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quote = ServiceQuote.objects.get(work_order=order)
        self.assertEqual(quote.total_parts, quote.items.filter(item_type=QuoteItem.ItemType.PART).first().total_price)
        self.assertEqual(quote.total_value, Decimal("600.00"))

    def test_approve_service_quote_updates_work_order(self):
        order = ServiceOrder.objects.create(
            order_number="SS-QTE-002",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.HIGH,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="OS aprovacao quote",
            created_by=self.user,
        )
        quote = ServiceQuote.objects.create(
            quote_number="QTE-2026-0001",
            company=self.maintenance_client.company,
            operational_site=self.site,
            work_order=order,
            asset=self.asset,
            status=ServiceQuote.Status.SENT,
            total_value="450.00",
            created_by=self.user,
            updated_by=self.user,
        )

        response = self.client.post(
            reverse("smart-system-service-quotes-approve-quote", kwargs={"pk": quote.pk}),
            {"approved_by_name": "Maintenance Manager", "approval_notes": "Aprovado para execucao."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(quote.status, ServiceQuote.Status.APPROVED)
        self.assertEqual(order.quote_status, ServiceQuote.Status.APPROVED)

    def test_reject_service_quote_updates_work_order(self):
        order = ServiceOrder.objects.create(
            order_number="SS-QTE-003",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.HIGH,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="OS rejeicao quote",
            created_by=self.user,
        )
        quote = ServiceQuote.objects.create(
            quote_number="QTE-2026-0002",
            company=self.maintenance_client.company,
            operational_site=self.site,
            work_order=order,
            asset=self.asset,
            status=ServiceQuote.Status.SENT,
            total_value="320.00",
            created_by=self.user,
            updated_by=self.user,
        )

        response = self.client.post(
            reverse("smart-system-service-quotes-reject-quote", kwargs={"pk": quote.pk}),
            {"approved_by_name": "Maintenance Manager", "rejection_reason": "Cliente nao aprovou o investimento."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(quote.status, ServiceQuote.Status.REJECTED)
        self.assertEqual(order.quote_status, ServiceQuote.Status.REJECTED)

    def test_unassigned_visits_endpoint_returns_suggestions(self):
        ScheduledVisit.objects.create(
            company=self.maintenance_client.company,
            operational_site=self.site,
            asset=self.asset,
            source_type=ScheduledVisit.SourceType.MANUAL,
            title="Visita pendente",
            scheduled_date=timezone.localdate(),
            priority=ScheduledVisit.Priority.MEDIUM,
            status=ScheduledVisit.Status.PENDING_ASSIGNMENT,
            city=self.site.city,
            state=self.site.state,
        )

        response = self.client.get(
            reverse("smart-system-scheduled-visits-unassigned"),
            {"date": timezone.localdate().isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["visit"]["title"], "Visita pendente")
        self.assertIn("suggested_technician", response.data[0])
        self.assertIn("visit", response.data[0])
