"""Filtros de escopo por unidade (OperationalSite) — regressão id_id inválido."""

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.smart_system.models import OperationalSite
from apps.smart_system.services.tenant_scope import SmartSystemScopeService
from tests.factories.core import CompanyFactory, MembershipFactory, SiteMembershipFactory, UserFactory
from tests.factories.smart_system import MaintenanceClientFactory, OperationalSiteFactory


class SiteFieldLookupTests(TestCase):
    def test_helpers_no_id_id_suffix(self):
        self.assertEqual(SmartSystemScopeService._site_pk_in_lookup("id"), "id__in")
        self.assertEqual(SmartSystemScopeService._site_pk_lookup("id"), "id")
        self.assertEqual(SmartSystemScopeService._site_pk_in_lookup("operational_site"), "operational_site_id__in")
        self.assertEqual(SmartSystemScopeService._site_pk_lookup("operational_site"), "operational_site_id")
        self.assertEqual(SmartSystemScopeService._site_pk_in_lookup("foo_bar_id"), "foo_bar_id__in")
        self.assertEqual(SmartSystemScopeService._site_pk_lookup("foo_bar_id"), "foo_bar_id")

    def test_scope_related_queryset_operational_site_evaluates_without_fielderror(self):
        bootstrap_smart_system_access()
        user = UserFactory(is_staff=True, password="passScope1!")
        company = CompanyFactory(slug="scope-os")
        MembershipFactory(user=user, company=company)
        assign_smart_system_role(user, "maintenance-manager")
        client = MaintenanceClientFactory(company=company, display_name="Cliente Escopo OS")
        mine = OperationalSiteFactory(maintenance_client=client, name="Meu local", code="M1")
        SiteMembershipFactory(user=user, company=company, site=mine)

        rf = RequestFactory()
        req = rf.get("/app/smart-system/inspection-routines/new/")
        req.user = user
        SessionMiddleware(lambda r: None).process_request(req)
        req.session.save()

        qs = SmartSystemScopeService.scope_related_queryset(OperationalSite, req)
        evaluated = list(qs.values_list("id", flat=True))
        self.assertIn(mine.id, evaluated)
        self.assertEqual(evaluated, [mine.id])


class InspectionRoutineNewWithSiteMembershipTests(TestCase):
    """restricted_to_sites=True exige filtros id__in nos OperationalSite."""

    def setUp(self):
        bootstrap_smart_system_access()

    def test_inspection_routines_new_returns_200_and_excludes_alien_site(self):
        user = UserFactory(is_staff=True, password="passScope2!")
        company = CompanyFactory(slug="tenant-scoped-sites")
        MembershipFactory(user=user, company=company)
        assign_smart_system_role(user, "maintenance-manager")
        client = MaintenanceClientFactory(company=company)
        allowed = OperationalSiteFactory(maintenance_client=client, name="Unidade permitida", code="OK1")
        SiteMembershipFactory(user=user, company=company, site=allowed)

        other_company = CompanyFactory(slug="outro-tenant-sc")
        alien_client = MaintenanceClientFactory(company=other_company, display_name="Alien cliente")
        alien_site = OperationalSiteFactory(maintenance_client=alien_client, name="UNIDADE-OUTRO-TENANT-X", code="BAD")

        self.client.force_login(user)
        resp = self.client.get(reverse("admin-shell:smart-system-inspection-routine-create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, allowed.name)
        self.assertNotContains(resp, alien_site.name)
