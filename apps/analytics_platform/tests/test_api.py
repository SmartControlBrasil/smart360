from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.analytics_platform.models import AnalyticsDashboard, AnalyticsEvent, AnalyticsMetric, AnalyticsMetricValue, AnalyticsWidget, OperationalMetrics
from apps.marketplace_technicians.models import TechnicianProfile, TechnicianReview
from apps.smart_system.models import MaintenanceContract, ServiceQuote, StockMovement, WorkLog
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory
from tests.factories.smart_system import AssetCategoryFactory, AssetFactory, MaintenanceClientFactory, OperationalSiteFactory, ServiceOrderFactory


class AnalyticsPlatformApiTests(APITestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.user = UserFactory(
            email="analytics@smart360.local",
            password="StrongPass123",
            first_name="Analytics",
        )
        self.company = CompanyFactory(name="Smart Analytics", slug="smart-analytics")
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)
        self.client.force_authenticate(self.user)

        self.metric = AnalyticsMetric.objects.create(
            metric_name="Total Service Orders",
            metric_type=AnalyticsMetric.MetricType.COUNTER,
            unit="orders",
        )
        self.maintenance_client = MaintenanceClientFactory(company=self.company, display_name="Cliente Premium")
        self.site = OperationalSiteFactory(maintenance_client=self.maintenance_client, name="Unidade Sul", code="SUL-01")
        self.asset = AssetFactory(
            operational_site=self.site,
            category=AssetCategoryFactory(name="HVAC Premium"),
            asset_tag="AST-ANA-001",
            name="Chiller Executivo",
        )
        self.order_completed = ServiceOrderFactory(
            order_number="OS-ANA-001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            created_by=self.user,
            maintenance_type="corrective",
            priority="high",
            status="completed",
            opened_at=timezone.now() - timedelta(hours=8),
            started_at=timezone.now() - timedelta(hours=6),
            completed_at=timezone.now() - timedelta(hours=2),
        )
        self.order_open = ServiceOrderFactory(
            order_number="OS-ANA-002",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            created_by=self.user,
            maintenance_type="preventive",
            priority="medium",
            status="in_progress",
        )
        WorkLog.objects.create(
            service_order=self.order_completed,
            user=self.user,
            started_at=self.order_completed.started_at,
            ended_at=self.order_completed.completed_at,
            labor_minutes=180,
        )
        part = self.company.smart_system_parts.create(
            code="PRT-ANA-001",
            name="Sensor Executivo",
            operational_site=self.site,
            unit_cost=Decimal("120.00"),
            current_stock=Decimal("10.00"),
            minimum_stock=Decimal("2.00"),
        )
        StockMovement.objects.create(
            company=self.company,
            operational_site=self.site,
            part=part,
            service_order=self.order_completed,
            movement_type=StockMovement.MovementType.OUTBOUND,
            quantity=Decimal("2.00"),
            performed_by=self.user,
        )
        self.contract = MaintenanceContract.objects.create(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-202603-0001",
            start_date=timezone.localdate() - timedelta(days=20),
            status=MaintenanceContract.Status.ACTIVE,
            billing_frequency=MaintenanceContract.BillingFrequency.MONTHLY,
            contract_value=Decimal("1500.00"),
        )
        ServiceQuote.objects.create(
            quote_number="QTE-ANA-001",
            company=self.company,
            operational_site=self.site,
            work_order=self.order_completed,
            asset=self.asset,
            status=ServiceQuote.Status.APPROVED,
            total_parts=Decimal("240.00"),
            total_labor=Decimal("300.00"),
            total_value=Decimal("540.00"),
            approved_at=timezone.now() - timedelta(days=1),
            approved_by_name="Cliente Premium",
            created_by=self.user,
            updated_by=self.user,
        )
        technician_profile = TechnicianProfile.objects.create(
            user=self.user,
            company=self.company,
            display_name="Tecnico Executivo",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
            rating_average=Decimal("4.70"),
            completed_jobs_count=20,
        )
        TechnicianReview.objects.create(
            assignment=None,
            reviewer_user=self.user,
            reviewer_company=self.company,
            technician_profile=technician_profile,
            rating=5,
            comment="Excelente atendimento",
            status=TechnicianReview.Status.PUBLISHED,
        )

    def test_create_analytics_event(self):
        response = self.client.post(
            reverse("analytics-events-list"),
            {
                "event_type": "service_order_created",
                "source_module": "smart_system",
                "entity_type": "service_order",
                "entity_id": "SO-20260311-0001",
                "user": self.user.id,
                "company": self.company.id,
                "payload": {"priority": "high"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AnalyticsEvent.objects.filter(event_type="service_order_created").exists())

    def test_create_metric_value(self):
        dimension = self.client.post(
            reverse("analytics-dimensions-list"),
            {"name": "City", "description": "Operational city slice", "is_active": True},
            format="json",
        )
        self.assertEqual(dimension.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            reverse("analytics-metric-values-list"),
            {
                "metric": self.metric.id,
                "dimension": dimension.data["id"] if "id" in dimension.data else None,
                "dimension_value": "Campinas",
                "value": "12.0000",
                "reference_date": "2026-03-11",
                "source_module": "smart_system",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AnalyticsMetricValue.objects.filter(metric=self.metric, dimension_value="Campinas").exists())

    def test_create_dashboard_and_widget(self):
        dashboard_response = self.client.post(
            reverse("analytics-dashboards-list"),
            {
                "name": "Operations Overview",
                "description": "Main KPI dashboard",
                "layout_config": {"columns": 12},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(dashboard_response.status_code, status.HTTP_201_CREATED)
        dashboard = AnalyticsDashboard.objects.get(name="Operations Overview")
        widget_response = self.client.post(
            reverse("analytics-widgets-list"),
            {
                "dashboard": dashboard.id,
                "widget_type": "metric_card",
                "title": "Service Orders",
                "metric": self.metric.id,
                "config_json": {"color": "blue"},
                "ordering": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(widget_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AnalyticsWidget.objects.filter(dashboard=dashboard, title="Service Orders").exists())

    def test_refresh_executive_metrics_creates_operational_snapshot(self):
        response = self.client.post(
            reverse("analytics-executive-refresh"),
            {"company": self.company.id, "period_type": "monthly"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        snapshot = OperationalMetrics.objects.get(company=self.company, period_type="monthly")
        self.assertGreater(snapshot.total_revenue, Decimal("0.00"))
        self.assertGreaterEqual(snapshot.total_cost, Decimal("0.00"))

    def test_executive_overview_returns_profitability_and_sla(self):
        self.client.post(reverse("analytics-executive-refresh"), {"company": self.company.id}, format="json")
        response = self.client.get(reverse("analytics-executive-overview"), {"company": self.company.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("kpis", response.data)
        self.assertIn("sla_summary", response.data)
        self.assertIn("top_clients", response.data)

    def test_revenue_profitability_technician_and_asset_endpoints(self):
        self.client.post(reverse("analytics-executive-refresh"), {"company": self.company.id}, format="json")
        revenue = self.client.get(reverse("analytics-revenue"), {"company": self.company.id})
        profitability = self.client.get(reverse("analytics-profitability"), {"company": self.company.id})
        technicians = self.client.get(reverse("analytics-technicians"), {"company": self.company.id})
        assets = self.client.get(reverse("analytics-assets"), {"company": self.company.id})
        self.assertEqual(revenue.status_code, status.HTTP_200_OK)
        self.assertEqual(profitability.status_code, status.HTTP_200_OK)
        self.assertEqual(technicians.status_code, status.HTTP_200_OK)
        self.assertEqual(assets.status_code, status.HTTP_200_OK)
        self.assertTrue(revenue.data["series"])
        self.assertIn("clients", profitability.data)
        self.assertIn("technicians", technicians.data)
        self.assertIn("assets", assets.data)

    def test_user_without_analytics_permission_gets_forbidden(self):
        outsider = UserFactory(email="outsider@smart360.local", password="StrongPass123")
        MembershipFactory(user=outsider, company=self.company, is_primary=True)
        assign_smart_system_role(outsider, "technician", company=self.company)
        self.client.force_authenticate(outsider)

        response = self.client.get(reverse("analytics-executive-overview"), {"company": self.company.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_access_analytics_of_unscoped_company(self):
        foreign_company = CompanyFactory(name="Foreign Analytics", slug="foreign-analytics")
        self.client.post(reverse("analytics-executive-refresh"), {"company": self.company.id}, format="json")

        response = self.client.get(reverse("analytics-executive-overview"), {"company": foreign_company.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
