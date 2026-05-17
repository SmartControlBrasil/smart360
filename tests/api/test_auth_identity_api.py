import pytest

from tests.factories.core import UserFactory


@pytest.mark.django_db
@pytest.mark.api
def test_auth_login_returns_token(client):
    user = UserFactory(email="login@smart360.local", password="admin123!")
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "admin123!", "device_label": "pytest"},
        format="json",
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.django_db
@pytest.mark.api
def test_identity_sessions_list_returns_current_user_sessions(authenticated_api_client):
    response = authenticated_api_client.get("/api/v1/identity/sessions/")
    assert response.status_code == 200

