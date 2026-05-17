import pytest

from tests.factories.notifications import NotificationMessageFactory


@pytest.mark.django_db
@pytest.mark.api
def test_notification_messages_list(authenticated_api_client):
    NotificationMessageFactory()
    response = authenticated_api_client.get("/api/v1/notifications/messages/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

