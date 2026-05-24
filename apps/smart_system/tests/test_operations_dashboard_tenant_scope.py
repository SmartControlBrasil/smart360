"""Isolamento multiempresa: dashboard de operação Smart System (Admin Shell SSR)."""

import json

from django.test import TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Membership
from apps.smart_system.models import ScheduledVisit
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory
from tests.factories.smart_system import (
    AssetFactory,
    MaintenanceClientFactory,
    OperationalSiteFactory,
    ScheduledVisitFactory,
    ServiceOrderFactory,
)


class OperationsDashboardTenantScopeTests(TestCase):
    """Garante /app/smart-system/operations/ só mostra dados do tenant do usuário."""

    def setUp(self):
        bootstrap_smart_system_access()

    def _staff_member(self, company, role_code="maintenance-manager"):
        user = UserFactory(is_staff=True, password="StrongPass123!")
        MembershipFactory(user=user, company=company)
        assign_smart_system_role(user, role_code)
        return user

    def test_operations_dashboard_zeros_and_other_tenant_os_hidden(self):
        company_other = CompanyFactory(name="Cliente Outro Tenant", slug="outro-tenant-os")
        company_b = CompanyFactory(name="Tenant B SaaS", slug="tenant-b-saas")
        user_b = self._staff_member(company_b)

        client_a = MaintenanceClientFactory(display_name="Cliente Alpha Oculto", company=company_other)
        site_a = OperationalSiteFactory(maintenance_client=client_a)
        asset_a = AssetFactory(operational_site=site_a)

        ServiceOrderFactory(
            order_number="ZZ-SHALL-NOT-APPEAR-ZZ",
            title="Titulo apenas outro tenant",
            client=client_a,
            operational_site=site_a,
            asset=asset_a,
        )

        self.client.force_login(user_b)
        url = reverse("admin-shell:smart-system-operations")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        decoded = resp.content.decode()
        self.assertNotIn("ZZ-SHALL-NOT-APPEAR-ZZ", decoded)
        self.assertNotIn("Titulo apenas outro tenant", decoded)

        chart = resp.context["operations_chart_data"]
        self.assertEqual(sum(chart["status"]["series"]), 0)

        fragments = decoded.split('"smart-system-operations-chart-data">')
        if len(fragments) > 1:
            blob = fragments[1].split("</script>", 1)[0].strip()
            chart_json = json.loads(blob)
            self.assertEqual(sum(chart_json["status"]["series"]), 0)

    def test_cross_tenant_work_order_numbers_not_visible(self):
        company_a = CompanyFactory(name="Firma Alpha", slug="firma-alpha")
        company_b = CompanyFactory(name="Firma Beta", slug="firma-beta")

        user_b = self._staff_member(company_b)

        client_a = MaintenanceClientFactory(company=company_a)
        site_a = OperationalSiteFactory(maintenance_client=client_a)

        ServiceOrderFactory(
            order_number="OS-TENANT-A-999",
            title="Titulo apenas Alpha",
            client=client_a,
            operational_site=site_a,
            asset=AssetFactory(operational_site=site_a),
        )

        self.client.force_login(user_b)
        resp = self.client.get(reverse("admin-shell:smart-system-operations"))
        self.assertEqual(resp.status_code, 200)
        decoded = resp.content.decode()
        self.assertNotIn("OS-TENANT-A-999", decoded)
        self.assertNotIn("Titulo apenas Alpha", decoded)

    def test_scheduled_visit_other_tenant_title_not_rendered_on_operations(self):
        company_a = CompanyFactory(slug="co-a-scope")
        company_b = CompanyFactory(slug="co-b-scope")

        user_b = self._staff_member(company_b)

        client_a = MaintenanceClientFactory(company=company_a)
        site_a = OperationalSiteFactory(maintenance_client=client_a)

        ScheduledVisitFactory(
            company=company_a,
            operational_site=site_a,
            asset=AssetFactory(operational_site=site_a),
            work_order=None,
            source_type=ScheduledVisit.SourceType.PREVENTIVE,
            title="VISITA_SIGILOSA_CO_A_PARA_ISO_TEST",
        )

        self.client.force_login(user_b)
        resp = self.client.get(reverse("admin-shell:smart-system-operations"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "VISITA_SIGILOSA_CO_A_PARA_ISO_TEST")

    def test_superuser_accesses_operations(self):
        su = UserFactory(is_superuser=True, is_staff=True, password="StrongPass123!")
        self.client.force_login(su)
        resp = self.client.get(reverse("admin-shell:smart-system-operations"))
        self.assertEqual(resp.status_code, 200)

    def test_smart_system_without_membership_gets_403(self):
        user = UserFactory(is_staff=True, password="StrongPass123!")
        assign_smart_system_role(user, "maintenance-manager")
        Membership.objects.filter(user=user).delete()
        CompanyFactory(slug="irrelevant-co")

        self.client.force_login(user)
        resp = self.client.get(reverse("admin-shell:smart-system-operations"))
        self.assertEqual(resp.status_code, 403)
