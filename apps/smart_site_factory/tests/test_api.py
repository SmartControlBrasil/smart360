from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.users.models import User

from ..models import ConfiguratorOption, ConfiguratorQuestion, Niche, ProductionTask, SiteOrder, Template, TemplateRecommendationRule


class SmartSiteFactoryApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="factory@smart360.local",
            password="StrongPass123",
            first_name="Factory",
        )
        self.company = Company.objects.create(name="Factory Co", slug="factory-co")
        self.niche = Niche.objects.create(name="Clinicas", slug="clinicas")
        self.template_a = Template.objects.create(
            niche=self.niche,
            name="Template Clinica A",
            slug="template-clinica-a",
            version="1.0.0",
            template_type=Template.TemplateType.ONE_PAGE,
            base_price="1990.00",
            status=Template.Status.READY,
        )
        self.question = ConfiguratorQuestion.objects.create(
            niche=self.niche,
            text="Quer agendamento online?",
            question_type=ConfiguratorQuestion.QuestionType.SINGLE_CHOICE,
            order=1,
        )
        self.option_yes = ConfiguratorOption.objects.create(
            question=self.question,
            label="Sim",
            value="yes",
            order=1,
        )
        TemplateRecommendationRule.objects.create(
            niche=self.niche,
            question=self.question,
            option=self.option_yes,
            recommended_template=self.template_a,
            priority=1,
        )
        self.client.force_authenticate(self.user)

    def test_create_site_order_generates_recommended_template_and_tasks(self):
        response = self.client.post(
            reverse("ssf-orders-list"),
            {
                "company": self.company.id,
                "niche": self.niche.id,
                "status": "intake_pending",
                "answers": [{"question": self.question.id, "option": self.option_yes.id}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recommended_template_slug"], self.template_a.slug)
        self.assertEqual(ProductionTask.objects.count(), 6)

    def test_create_intake(self):
        order_response = self.client.post(
            reverse("ssf-orders-list"),
            {"company": self.company.id, "niche": self.niche.id},
            format="json",
        )
        order_id = order_response.data["public_id"]
        order_pk = self.user.site_orders.first().id

        response = self.client.post(
            reverse("ssf-intakes-list"),
            {
                "site_order": order_pk,
                "company_name": "Factory Co",
                "city": "Sao Paulo",
                "state": "SP",
                "main_services": ["Consulta", "Retorno"],
                "photo_gallery": ["https://example.com/photo-1.jpg"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company_name"], "Factory Co")
        self.assertTrue(order_id)

    def test_start_production_task_updates_order_status(self):
        self.client.post(
            reverse("ssf-orders-list"),
            {"company": self.company.id, "niche": self.niche.id},
            format="json",
        )
        order = SiteOrder.objects.first()
        task = order.production_tasks.order_by("order").first()

        response = self.client.post(reverse("ssf-production-start", kwargs={"pk": task.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, SiteOrder.Status.IN_PRODUCTION)
