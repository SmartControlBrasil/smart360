from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import (
    EquipmentReference,
    FailureActionMap,
    FailureReference,
    KnowledgeCategory,
    RecommendedAction,
    SymptomFailureMap,
    SymptomReference,
    TroubleshootingArticle,
)


class KnowledgeEngineApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="knowledge@smart360.local",
            password="StrongPass123",
            first_name="Knowledge",
        )
        self.client.force_authenticate(self.user)
        self.category = KnowledgeCategory.objects.create(name="Troubleshooting")
        self.symptom = SymptomReference.objects.create(name="Vibracao elevada")
        self.failure = FailureReference.objects.create(name="Desbalanceamento")
        self.action = RecommendedAction.objects.create(title="Balancear rotor")

    def test_create_article(self):
        response = self.client.post(
            reverse("knowledge-troubleshooting-articles-list"),
            {
                "title": "Como tratar vibracao elevada",
                "category": self.category.id,
                "summary": "Passos iniciais",
                "content": "Conteudo estruturado do artigo",
                "status": "published",
                "created_by": self.user.id,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TroubleshootingArticle.objects.filter(title="Como tratar vibracao elevada").exists())

    def test_create_maps(self):
        symptom_failure_response = self.client.post(
            reverse("knowledge-symptom-failure-maps-list"),
            {
                "symptom_reference": self.symptom.id,
                "failure_reference": self.failure.id,
                "confidence_level": "85.50",
            },
            format="json",
        )
        failure_action_response = self.client.post(
            reverse("knowledge-failure-action-maps-list"),
            {
                "failure_reference": self.failure.id,
                "recommended_action": self.action.id,
                "priority": 1,
            },
            format="json",
        )

        self.assertEqual(symptom_failure_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(failure_action_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SymptomFailureMap.objects.filter(symptom_reference=self.symptom, failure_reference=self.failure).exists())
        self.assertTrue(FailureActionMap.objects.filter(failure_reference=self.failure, recommended_action=self.action).exists())

    def test_create_equipment_and_feedback(self):
        equipment_response = self.client.post(
            reverse("knowledge-equipments-list"),
            {
                "name": "Motor Inducao 50CV",
                "manufacturer": "WEG",
                "model": "W22",
                "equipment_type": "motor",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(equipment_response.status_code, status.HTTP_201_CREATED)
        equipment = EquipmentReference.objects.get(name="Motor Inducao 50CV")

        feedback_response = self.client.post(
            reverse("knowledge-feedback-list"),
            {
                "user": self.user.id,
                "item_type": "equipment",
                "item_id": equipment.id,
                "usefulness_rating": 5,
                "comment": "Muito util",
            },
            format="json",
        )
        self.assertEqual(feedback_response.status_code, status.HTTP_201_CREATED)
