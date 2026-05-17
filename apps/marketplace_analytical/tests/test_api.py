from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite, ServiceOrder
from apps.users.models import User

from ..models import (
    AnalyticalAssignment,
    AnalyticalProvider,
    AnalyticalRequest,
    AnalyticalReview,
    AnalyticalService,
    AnalyticalServiceCategory,
    AnalyticalServiceCapability,
)


class MarketplaceAnalyticalApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="analytical@smart360.local",
            password="StrongPass123",
            first_name="Analytical",
        )
        self.company = Company.objects.create(name="Lab Experts", slug="lab-experts")
        self.client.force_authenticate(self.user)
        self.provider = AnalyticalProvider.objects.create(
            company=self.company,
            user=self.user,
            display_name="Lab Experts",
            provider_type=AnalyticalProvider.ProviderType.LABORATORY,
            verification_status=AnalyticalProvider.VerificationStatus.APPROVED,
            marketplace_status=AnalyticalProvider.MarketplaceStatus.AVAILABLE,
        )
        self.category = AnalyticalServiceCategory.objects.create(name="Vibration Analysis")
        self.maintenance_client = MaintenanceClient.objects.create(display_name="Industria Gama")
        self.site = OperationalSite.objects.create(maintenance_client=self.maintenance_client, name="Planta Gama", city="Campinas", state="SP")
        self.asset_category = AssetCategory.objects.create(name="Compressores")
        self.asset = Asset.objects.create(operational_site=self.site, category=self.asset_category, asset_tag="CMP-001", name="Compressor 01")
        self.service_order = ServiceOrder.objects.create(
            order_number="SS-TEST-AN-0001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_type=ServiceOrder.MaintenanceType.INSPECTION,
            priority=ServiceOrder.Priority.MEDIUM,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="Inspecao complementar",
            created_by=self.user,
        )

    def test_create_analytical_service_and_capability(self):
        service_response = self.client.post(
            reverse("marketplace-analytical-services-list"),
            {
                "provider": self.provider.id,
                "category": self.category.id,
                "title": "Analise espectral de vibracao",
                "description": "Relatorio espectral completo",
                "service_type": "analysis",
                "delivery_type": "remote",
                "estimated_turnaround_days": 3,
                "price_model": "fixed",
                "base_price": "2500.00",
                "currency": "BRL",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED)
        service = AnalyticalService.objects.get(title="Analise espectral de vibracao")

        capability_response = self.client.post(
            reverse("marketplace-analytical-capabilities-list"),
            {
                "analytical_service": service.id,
                "capability_name": "Analise espectral",
                "description": "FFT e envelope",
            },
            format="json",
        )
        self.assertEqual(capability_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AnalyticalServiceCapability.objects.filter(analytical_service=service).exists())

    def test_assignment_flow_completes_request(self):
        analytical_request = AnalyticalRequest.objects.create(
            requester_user=self.user,
            requester_company=self.company,
            title="Diagnostico de vibracao",
            description="Avaliar nivel de vibracao do ativo",
            category=self.category,
            priority=AnalyticalRequest.Priority.HIGH,
            related_asset=self.asset,
            related_site=self.site,
            related_service_order=self.service_order,
            city="Campinas",
            state="SP",
            origin=AnalyticalRequest.Origin.SMART_SYSTEM,
            status=AnalyticalRequest.Status.MATCHING,
        )

        response = self.client.post(
            reverse("marketplace-analytical-assignments-list"),
            {
                "analytical_request": analytical_request.id,
                "provider": self.provider.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = AnalyticalAssignment.objects.get(analytical_request=analytical_request, provider=self.provider)

        accept_response = self.client.post(reverse("marketplace-analytical-assignments-accept", kwargs={"pk": assignment.pk}), format="json")
        complete_response = self.client.post(reverse("marketplace-analytical-assignments-complete", kwargs={"pk": assignment.pk}), format="json")

        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        assignment.refresh_from_db()
        analytical_request.refresh_from_db()
        self.assertEqual(assignment.status, AnalyticalAssignment.Status.COMPLETED)
        self.assertEqual(analytical_request.status, AnalyticalRequest.Status.DELIVERED)

    def test_review_updates_provider_rating(self):
        analytical_request = AnalyticalRequest.objects.create(
            title="Analise de oleo",
            description="Coleta e analise de amostra",
            category=self.category,
            city="Campinas",
            state="SP",
        )
        assignment = AnalyticalAssignment.objects.create(
            analytical_request=analytical_request,
            provider=self.provider,
            status=AnalyticalAssignment.Status.COMPLETED,
        )

        response = self.client.post(
            reverse("marketplace-analytical-reviews-list"),
            {
                "analytical_assignment": assignment.id,
                "reviewer_user": self.user.id,
                "reviewer_company": self.company.id,
                "rating": 5,
                "comment": "Entrega excelente",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.rating_average, Decimal("5"))
