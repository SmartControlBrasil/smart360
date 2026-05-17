from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Company, Membership, SiteMembership
from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceRegion,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
    ServiceRegion,
)
from apps.marketplace_technicians.services.marketplace_service import TechnicianMatchingService
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite
from apps.users.models import User


class MarketplaceTechniciansApiTests(APITestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.company_user = User.objects.create_user(
            email="empresa@smart360.local",
            password="StrongPass123",
            first_name="Empresa",
        )
        self.technician_user = User.objects.create_user(
            email="tech@smart360.local",
            password="StrongPass123",
            first_name="Tecnico",
        )
        self.company = Company.objects.create(name="Industria Beta", slug="industria-beta")
        Membership.objects.create(
            user=self.company_user,
            company=self.company,
            status=Membership.Status.ACTIVE,
            is_primary=True,
        )
        assign_smart_system_role(self.company_user, "maintenance-manager", company=self.company)
        assign_smart_system_role(self.technician_user, "technician")

        self.maintenance_client = MaintenanceClient.objects.create(company=self.company, display_name="Industria Beta")
        self.site = OperationalSite.objects.create(
            maintenance_client=self.maintenance_client,
            name="Planta 01",
            code="PLT-01",
            city="Sao Paulo",
            state="SP",
        )
        SiteMembership.objects.create(
            user=self.company_user,
            company=self.company,
            site=self.site,
            status=SiteMembership.Status.ACTIVE,
            is_primary=True,
        )
        self.category = AssetCategory.objects.create(name="Bombas")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="BMB-001",
            name="Bomba A",
        )
        self.profile = TechnicianProfile.objects.create(
            user=self.technician_user,
            display_name="Tecnico Marcelo",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
            service_radius_km=50,
            rating_average="4.80",
            completed_jobs_count=9,
        )
        self.skill = TechnicianSkill.objects.create(name="bombas")
        TechnicianSkillAssignment.objects.create(
            technician_profile=self.profile,
            skill=self.skill,
        )
        self.region = ServiceRegion.objects.create(
            name="Sao Paulo Capital",
            state="SP",
            city="Sao Paulo",
        )
        TechnicianServiceRegion.objects.create(
            technician_profile=self.profile,
            service_region=self.region,
        )

    def test_company_user_creates_service_request(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            reverse("marketplace-technicians-service-requests-list"),
            {
                "title": "Falha em bomba",
                "description": "Necessario atendimento em campo",
                "category": "bombas",
                "service_type": "maintenance",
                "priority": "high",
                "city": "Sao Paulo",
                "state": "SP",
                "location_label": "Area de utilidades",
                "related_site": self.site.id,
                "related_asset": self.asset.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service_request = TechnicianServiceRequest.objects.get(public_id=response.data["public_id"])
        self.assertEqual(service_request.requester_company, self.company)
        self.assertEqual(service_request.status, TechnicianServiceRequest.Status.MATCHING)
        self.assertTrue(
            TechnicianMatchingRecord.objects.filter(
                technician_service_request=service_request,
                technician_profile=self.profile,
            ).exists()
        )

    def test_technician_submits_offer_and_company_accepts(self):
        service_request = TechnicianServiceRequest.objects.create(
            requester_user=self.company_user,
            requester_company=self.company,
            title="Chiller parado",
            description="Marketplace para corretiva",
            category="chiller",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.OPEN,
        )

        self.client.force_authenticate(self.technician_user)
        offer_response = self.client.post(
            reverse("marketplace-technicians-service-offers-list"),
            {
                "service_request": service_request.id,
                "technician_profile": self.profile.id,
                "proposed_amount": "450.00",
                "message": "Posso atender hoje no periodo da tarde.",
                "estimated_hours": 4,
            },
            format="json",
        )

        self.assertEqual(offer_response.status_code, status.HTTP_201_CREATED)
        offer = TechnicianServiceOffer.objects.get(public_id=offer_response.data["public_id"])
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, TechnicianServiceRequest.Status.OFFERS_RECEIVED)

        self.client.force_authenticate(self.company_user)
        accept_response = self.client.post(
            reverse("marketplace-technicians-service-offers-accept", kwargs={"pk": offer.pk}),
            format="json",
        )

        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        assignment = TechnicianAssignment.objects.get(service_offer=offer)
        self.assertEqual(assignment.assignment_status, TechnicianAssignment.AssignmentStatus.ASSIGNED)
        self.assertIsNotNone(assignment.technician_service_request.related_service_order)

    def test_assignment_completion_and_review_updates_rating(self):
        service_request = TechnicianServiceRequest.objects.create(
            requester_user=self.company_user,
            requester_company=self.company,
            title="Inspecao tecnica",
            description="Demanda pronta para atribuicao",
            category="inspecao",
            service_type=TechnicianServiceRequest.ServiceType.INSPECTION,
            priority=TechnicianServiceRequest.Priority.MEDIUM,
            city="Sao Paulo",
            state="SP",
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.ASSIGNED,
        )
        assignment = TechnicianAssignment.objects.create(
            technician_service_request=service_request,
            technician_profile=self.profile,
            assignment_status=TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
        )

        self.client.force_authenticate(self.technician_user)
        complete_response = self.client.post(
            reverse("marketplace-technicians-assignments-complete", kwargs={"pk": assignment.pk}),
            format="json",
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.company_user)
        review_response = self.client.post(
            reverse("marketplace-technicians-reviews-list"),
            {
                "assignment": assignment.id,
                "reviewer_user": self.company_user.id,
                "reviewer_company": self.company.id,
                "rating": 5,
                "comment": "Excelente atendimento",
                "status": "published",
            },
            format="json",
        )

        self.assertEqual(review_response.status_code, status.HTTP_201_CREATED)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rating_average, Decimal("5"))
        self.assertTrue(
            TechnicianReview.objects.filter(
                assignment=assignment,
                technician_profile=self.profile,
                reviewer_company=self.company,
            ).exists()
        )

    def test_matching_ranks_best_technician_first(self):
        second_user = User.objects.create_user(
            email="tech2@smart360.local",
            password="StrongPass123",
            first_name="Tecnico 2",
        )
        second_profile = TechnicianProfile.objects.create(
            user=second_user,
            display_name="Tecnico Reserva",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.BUSY,
            service_radius_km=20,
            rating_average="3.20",
            completed_jobs_count=1,
        )
        TechnicianServiceRegion.objects.create(
            technician_profile=second_profile,
            service_region=self.region,
        )
        request = TechnicianServiceRequest.objects.create(
            requester_user=self.company_user,
            requester_company=self.company,
            title="Falha em bomba de recalque",
            description="Servico para motor de bomba",
            category="bombas",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.OPEN,
        )
        TechnicianMatchingService.refresh_matches(service_request=request)

        ranking = list(
            TechnicianMatchingRecord.objects.filter(
                technician_service_request=request
            ).order_by("ranking_position", "-match_score")
        )
        self.assertGreaterEqual(len(ranking), 2)
        self.assertEqual(ranking[0].technician_profile_id, self.profile.id)
        self.assertGreater(ranking[0].score_specialty, ranking[1].score_specialty)

    def test_request_matching_endpoint_returns_ranked_records(self):
        request = TechnicianServiceRequest.objects.create(
            requester_user=self.company_user,
            requester_company=self.company,
            title="Falha em bomba pressurizadora",
            description="Ranking automatico requerido",
            category="bombas",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            status=TechnicianServiceRequest.Status.OPEN,
        )
        TechnicianMatchingService.refresh_matches(service_request=request)

        self.client.force_authenticate(self.company_user)
        response = self.client.get(
            reverse("marketplace-technicians-service-requests-matching", kwargs={"pk": request.pk}),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn("score_specialty", response.data[0])
        self.assertIn("ranking_position", response.data[0])
