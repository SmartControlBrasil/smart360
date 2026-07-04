from django.urls import reverse
from django.test import TestCase
from tests.factories.core import UserFactory, CompanyFactory
from apps.companies.models import Membership
from apps.ai_agents_center.models import AtlasProspectImportBatch, CommercialOpportunity

class AtlasImportsAdminShellTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="operator@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas Corp", slug="atlas-corp")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)
        self.client.force_login(self.user)

        self.batch = AtlasProspectImportBatch.objects.create(
            company=self.company,
            created_by=self.user,
            source="google_maps",
            filename="escolas_saopaulo.csv",
            total_rows=10,
            processed_rows=10,
            created_opportunities=4,
            skipped_duplicates=4,
            errors=[{"row": 5, "company_name": "Escola Falha", "error": "Missing key contacts"}],
            status=AtlasProspectImportBatch.Status.COMPLETED
        )

        self.opportunity = CommercialOpportunity.objects.create(
            company=self.company,
            company_name="Escola Inovacao",
            source="google_maps",
            problem_detected="Limpeza estrutural",
            commercial_score=80,
            confidence_score=0.75,
            metadata={
                "import_batch_public_id": str(self.batch.public_id),
                "origin_agent": "atlas-commercial-intelligence-agent"
            }
        )

    def test_imports_list_view_loads_and_displays_batch(self):
        response = self.client.get(reverse("admin-shell:atlas-imports"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/atlas_imports.html")
        self.assertContains(response, "Importações Atlas")
        self.assertContains(response, str(self.batch.public_id))
        self.assertContains(response, "Google Maps")
        self.assertContains(response, "<td>10</td>")
        self.assertContains(response, "<td>4</td>")

    def test_imports_detail_view_loads_and_displays_details_and_errors(self):
        response = self.client.get(reverse("admin-shell:atlas-import-detail", kwargs={"public_id": self.batch.public_id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/atlas_import_detail.html")
        self.assertContains(response, str(self.batch.public_id))
        self.assertContains(response, "Escola Falha")
        self.assertContains(response, "Missing key contacts")
        self.assertContains(response, "5")

    def test_opportunity_link_filters_correctly(self):
        response = self.client.get(reverse("admin-shell:atlas-opportunities") + f"?batch={self.batch.public_id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Escola Inovacao")
        content = response.content.decode("utf-8")
        self.assertNotIn("AtlasLead", content)
        self.assertNotIn("PendingAtlasLead", content)

    def test_permissions_are_enforced(self):
        self.client.logout()
        response = self.client.get(reverse("admin-shell:atlas-imports"))
        self.assertEqual(response.status_code, 302)
