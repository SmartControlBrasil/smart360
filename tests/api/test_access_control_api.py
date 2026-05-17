import pytest

from tests.factories.access_control import PermissionActionFactory, PermissionDomainFactory


@pytest.mark.django_db
@pytest.mark.api
def test_access_control_check_permission_endpoint(authenticated_admin_client, role_permission_context):
    domain = role_permission_context["domain"]
    action = role_permission_context["action"]
    company = role_permission_context["company"]
    response = authenticated_admin_client.post(
        "/api/v1/access-control/check-permission/",
        {
            "domain_slug": domain.slug,
            "action_slug": action.slug,
            "company": company.id,
            "module_name": domain.module_name,
        },
        format="json",
    )
    assert response.status_code == 200
    assert "allowed" in response.json()

