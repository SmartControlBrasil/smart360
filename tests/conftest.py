import pytest
from rest_framework.test import APIClient

from tests.factories.access_control import (
    AccessRoleFactory,
    PermissionActionFactory,
    PermissionDomainFactory,
    RolePermissionFactory,
    UserRoleAssignmentFactory,
)
from tests.factories.core import CompanyFactory, MembershipFactory, RoleFactory, UserFactory
from tests.factories.growth import LeadFactory, LeadSourceFactory
from tests.factories.market_core import MarketplaceOrderFactory, MarketplaceProductFactory, MarketplaceVendorFactory
from tests.factories.smart_system import (
    AssetFactory,
    AssetCategoryFactory,
    MaintenanceClientFactory,
    OperationalSiteFactory,
    ServiceOrderFactory,
)
from tests.helpers import authenticate_client


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return UserFactory(email="admin@smart360.local", is_staff=True, is_superuser=True)


@pytest.fixture
def demo_user(db):
    return UserFactory(email="demo@smart360.local")


@pytest.fixture
def internal_company(db):
    return CompanyFactory(name="Smart360 Internal", slug="smart360-internal")


@pytest.fixture
def demo_company(db):
    return CompanyFactory(name="Demo Company", slug="demo-company")


@pytest.fixture
def membership(db, demo_user, demo_company):
    role = RoleFactory(code="company_admin", label="Company Admin")
    return MembershipFactory(user=demo_user, company=demo_company, roles=[role])


@pytest.fixture
def authenticated_api_client(db, demo_user):
    return authenticate_client(demo_user)


@pytest.fixture
def authenticated_admin_client(db, admin_user):
    return authenticate_client(admin_user)


@pytest.fixture
def role_permission_context(db, admin_user, internal_company):
    role = AccessRoleFactory(name="Finance Admin")
    domain = PermissionDomainFactory(module_name="billing", name="Billing")
    action = PermissionActionFactory(domain=domain, action_name="approve")
    RolePermissionFactory(role=role, permission_domain=domain, permission_action=action, is_allowed=True)
    UserRoleAssignmentFactory(user=admin_user, role=role, company=internal_company)
    return {
        "role": role,
        "domain": domain,
        "action": action,
        "company": internal_company,
        "user": admin_user,
    }


@pytest.fixture
def marketplace_scenario(db, demo_user, demo_company):
    vendor = MarketplaceVendorFactory(company=demo_company, owner=demo_user)
    product = MarketplaceProductFactory(vendor=vendor)
    order = MarketplaceOrderFactory(customer=demo_user, company=demo_company)
    lead_source = LeadSourceFactory()
    lead = LeadFactory(source=lead_source, created_by=demo_user, assigned_to=demo_user)
    return {
        "vendor": vendor,
        "product": product,
        "order": order,
        "lead": lead,
    }


@pytest.fixture
def smart_system_scenario(db, demo_company, demo_user):
    client = MaintenanceClientFactory(company=demo_company)
    site = OperationalSiteFactory(maintenance_client=client)
    category = AssetCategoryFactory()
    asset = AssetFactory(operational_site=site, category=category)
    service_order = ServiceOrderFactory(client=client, operational_site=site, asset=asset, created_by=demo_user)
    return {
        "client": client,
        "site": site,
        "asset_category": category,
        "asset": asset,
        "service_order": service_order,
    }
