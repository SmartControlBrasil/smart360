from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import SearchIndexEntry, SearchQueryLog


class GlobalSearchApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="search@smart360.local",
            password="StrongPass123",
            first_name="Search",
        )
        self.client.force_authenticate(self.user)

    def test_create_index_entry_and_query(self):
        create_response = self.client.post(
            reverse("search-index-entries-list"),
            {
                "source_module": "smart_system",
                "item_type": "service_order",
                "item_id": "SO-100",
                "title": "Service Order SO-100",
                "subtitle": "Corrective maintenance",
                "body_text": "Open service order for compressor",
                "search_text": "service order compressor corrective maintenance",
                "status": "open",
                "category": "maintenance",
                "url_path": "/smart-system/service-orders/SO-100/",
                "metadata": {"priority": "high"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        query_response = self.client.get(reverse("search-query"), {"q": "compressor"})
        self.assertEqual(query_response.status_code, status.HTTP_200_OK)
        self.assertEqual(query_response.data["count"], 1)
        self.assertTrue(SearchQueryLog.objects.filter(query_text="compressor").exists())

    def test_autocomplete_returns_matches(self):
        SearchIndexEntry.objects.create(
            source_module="knowledge_engine",
            item_type="technical_document",
            item_id="DOC-1",
            title="Manual do Compressor",
            body_text="Manual tecnico",
            search_text="manual compressor tecnico",
            status="published",
            category="technical_document",
            is_active=True,
        )
        response = self.client.get(reverse("search-autocomplete"), {"q": "Manual"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_synonym_expands_query(self):
        self.client.post(
            reverse("search-synonyms-list"),
            {"term": "OS", "synonym": "ordem", "is_active": True},
            format="json",
        )
        SearchIndexEntry.objects.create(
            source_module="smart_system",
            item_type="service_order",
            item_id="SO-101",
            title="Ordem de servico 101",
            body_text="Corretiva",
            search_text="ordem servico corretiva",
            status="open",
            category="maintenance",
            is_active=True,
        )
        response = self.client.get(reverse("search-query"), {"q": "OS"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

