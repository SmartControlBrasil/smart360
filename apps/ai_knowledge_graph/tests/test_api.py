from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_knowledge_graph.services.graph import GraphProjectionService
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, FailureEventFactory, OperationalSiteFactory, ServiceOrderFactory


class KnowledgeGraphApiTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)
        self.site = OperationalSiteFactory()
        self.company = self.site.maintenance_client.company
        self.asset = AssetFactory(operational_site=self.site)
        self.order = ServiceOrderFactory(client=self.site.maintenance_client, operational_site=self.site, asset=self.asset, assigned_to=self.user)
        self.failure = FailureEventFactory(asset=self.asset, service_order=self.order)
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)
        self.client.force_authenticate(self.user)
        GraphProjectionService.project_company_graph(company=self.company, site=self.site)

    def test_context_endpoint_returns_relational_payload(self):
        response = self.client.get(
            reverse("knowledge-graph-node-context"),
            {"company": self.company.id, "entity_type": "asset", "entity_id": str(self.asset.public_id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("node", response.data)
        self.assertIn("neighbors", response.data)

    def test_subgraph_endpoint_returns_nodes_and_edges(self):
        context_response = self.client.get(
            reverse("knowledge-graph-node-context"),
            {"company": self.company.id, "entity_type": "asset", "entity_id": str(self.asset.public_id)},
        )
        node_public_id = context_response.data["node"]["public_id"]
        response = self.client.get(reverse("knowledge-graph-node-subgraph"), {"company": self.company.id, "entity_type": "asset", "entity_id": str(self.asset.public_id)})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["nodes"]), 1)
        self.assertGreaterEqual(len(response.data["edges"]), 1)

    def test_list_nodes_is_scoped(self):
        response = self.client.get(reverse("knowledge-graph-node-list"), {"company": self.company.id})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)
