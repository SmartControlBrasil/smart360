from django.test import TestCase

from apps.access_control_center.models import PermissionDomain, Role, RolePermission
from apps.access_control_center.services.smart_system_access import (
    assign_smart_system_role,
    bootstrap_smart_system_access,
    get_smart_system_permission_map,
)
from tests.factories.core import UserFactory


class SmartSystemAccessBootstrapTests(TestCase):
    def test_bootstrap_creates_matrix(self):
        summary = bootstrap_smart_system_access()

        self.assertGreaterEqual(summary["domains"], 11)
        self.assertTrue(PermissionDomain.objects.filter(slug="assets").exists())
        self.assertTrue(PermissionDomain.objects.filter(slug="billing_admin").exists())
        self.assertTrue(Role.objects.filter(slug="maintenance-manager").exists())
        self.assertTrue(
            RolePermission.objects.filter(
                role__slug="technician",
                permission_domain__slug="work_execution",
                permission_action__action_name="execute",
                is_allowed=True,
            ).exists()
        )

    def test_permission_map_respects_role_profile(self):
        bootstrap_smart_system_access()
        user = UserFactory()
        assign_smart_system_role(user, "technician")

        permission_map = get_smart_system_permission_map(user)

        self.assertTrue(permission_map["work_execution.execute"])
        self.assertTrue(permission_map["inventory.consume"])
        self.assertFalse(permission_map["inventory.adjust_stock"])
        self.assertFalse(permission_map["users.manage"])
        self.assertFalse(permission_map["billing_admin.view"])

    def test_finance_readonly_can_view_billing_but_not_manage(self):
        bootstrap_smart_system_access()
        user = UserFactory()
        assign_smart_system_role(user, "finance-readonly")

        permission_map = get_smart_system_permission_map(user)

        self.assertTrue(permission_map["billing_admin.view"])
        self.assertTrue(permission_map["billing_admin.export"])
        self.assertFalse(permission_map["billing_admin.manage"])

    def test_company_admin_cannot_view_platform_observability(self):
        bootstrap_smart_system_access()
        user = UserFactory()
        assign_smart_system_role(user, "company-admin")

        permission_map = get_smart_system_permission_map(user)

        self.assertFalse(permission_map["observability_admin.view"])
