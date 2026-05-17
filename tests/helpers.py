from rest_framework.test import APIClient

from apps.companies.models import Membership


def authenticate_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_company_membership(*, user, company, role=None, is_primary=True):
    membership, _ = Membership.objects.get_or_create(
        user=user,
        company=company,
        defaults={"status": Membership.Status.ACTIVE, "is_primary": is_primary},
    )
    if role:
        membership.roles.add(role)
    return membership

