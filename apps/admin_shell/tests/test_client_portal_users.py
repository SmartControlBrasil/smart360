from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite, ServiceOrder


class ClientPortalUserAdminTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            email="staff-client-users@smart360.local",
            password="StrongPass123",
            first_name="Staff",
            is_staff=True,
            user_type="internal",
        )
        self.company = Company.objects.create(name="Cliente Admin Shell", slug="cliente-admin-shell")
        self.maintenance_client = MaintenanceClient.objects.create(
            company=self.company,
            display_name="Cliente Admin Shell",
        )
        self.site = OperationalSite.objects.create(maintenance_client=self.maintenance_client, name="Unidade A")
        Membership.objects.create(user=self.staff, company=self.company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(
            user=self.staff,
            company=self.company,
            site=self.site,
            status=SiteMembership.Status.ACTIVE,
            is_primary=True,
        )

    def login_staff(self):
        self.client.force_login(self.staff)

    def portal_user_payload(self, **overrides):
        payload = {
            "full_name": "Maria Portal",
            "email": "maria.portal@cliente.test",
            "company": self.company.pk,
            "site": self.site.pk,
            "access_level": "client-manager",
            "is_active": "on",
            "password": "TempPass123",
        }
        payload.update(overrides)
        return payload

    def create_portal_user(self, *, email="cliente.portal@smart360.local", group="client-readonly"):
        user = get_user_model().objects.create_user(
            email=email,
            password="StrongPass123",
            first_name="Cliente",
            user_type="client",
        )
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        Membership.objects.create(user=user, company=self.company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(
            user=user,
            company=self.company,
            site=self.site,
            status=SiteMembership.Status.ACTIVE,
            is_primary=True,
        )
        return user

    def test_internal_staff_accesses_client_user_listing(self):
        self.login_staff()

        response = self.client.get(reverse("admin-shell:client-portal-users"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuários do Portal")
        self.assertContains(response, "Eles não acessam o painel interno do Smart360")

    def test_client_portal_only_user_is_redirected_from_listing_to_portal(self):
        user = self.create_portal_user(group="client-portal-only")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-users"))

        self.assertRedirects(response, "/portal/", fetch_redirect_response=False)

    def test_create_client_portal_user_sets_type_group_flags_and_scope(self):
        self.login_staff()

        response = self.client.post(
            reverse("admin-shell:client-portal-user-create"),
            self.portal_user_payload(access_level="client-manager"),
        )

        self.assertRedirects(response, reverse("admin-shell:client-portal-users"))
        user = get_user_model().objects.get(email="maria.portal@cliente.test")
        self.assertEqual(user.user_type, "client")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name="client-manager").exists())
        self.assertTrue(Membership.objects.filter(user=user, company=self.company, status=Membership.Status.ACTIVE).exists())
        self.assertTrue(SiteMembership.objects.filter(user=user, site=self.site, status=SiteMembership.Status.ACTIVE).exists())

    def test_edit_client_portal_user_changes_access_level(self):
        user = self.create_portal_user(group="client-readonly")
        self.login_staff()

        response = self.client.post(
            reverse("admin-shell:client-portal-user-update", args=[user.pk]),
            self.portal_user_payload(
                full_name="Cliente Gestor",
                email=user.email,
                access_level="client-manager",
                password="",
            ),
        )

        self.assertRedirects(response, reverse("admin-shell:client-portal-users"))
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name="client-manager").exists())
        self.assertFalse(user.groups.filter(name="client-readonly").exists())

    def test_listing_shows_created_client_user(self):
        user = self.create_portal_user(email="lista.portal@smart360.local", group="client-manager")
        self.login_staff()

        response = self.client.get(reverse("admin-shell:client-portal-users"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, user.email)
        self.assertContains(response, "Gestor da unidade")

    def test_readonly_group_cannot_create_service_order(self):
        user = self.create_portal_user(group="client-readonly")
        category = AssetCategory.objects.create(name="Categoria Readonly", slug="categoria-readonly")
        asset = Asset.objects.create(
            operational_site=self.site,
            category=category,
            asset_tag="RO-001",
            name="Ativo readonly",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("technical_portal:service-order-create"),
            {
                "operational_site": self.site.pk,
                "asset": asset.pk,
                "priority": ServiceOrder.Priority.HIGH,
                "description": "Falha relatada por usuário somente leitura.",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ServiceOrder.objects.exists())

    def test_client_manager_group_can_create_service_order(self):
        user = self.create_portal_user(group="client-manager")
        category = AssetCategory.objects.create(name="Categoria Manager", slug="categoria-manager")
        asset = Asset.objects.create(
            operational_site=self.site,
            category=category,
            asset_tag="MG-001",
            name="Ativo manager",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("technical_portal:service-order-create"),
            {
                "operational_site": self.site.pk,
                "asset": asset.pk,
                "priority": ServiceOrder.Priority.HIGH,
                "description": "Falha relatada por gestor da unidade.",
            },
        )

        self.assertRedirects(response, reverse("technical_portal:service-orders"))
        order = ServiceOrder.objects.get()
        self.assertEqual(order.client, self.maintenance_client)
        self.assertEqual(order.operational_site, self.site)
        self.assertEqual(order.asset, asset)
