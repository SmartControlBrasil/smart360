from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.companies.models import Company, Membership
from apps.roles.models import Role


class CompanyService:
    @staticmethod
    @transaction.atomic
    def create_company_with_owner(*, user, validated_data):
        role_codes = validated_data.pop("role_codes", ["company_owner"])
        company = Company.objects.create(**validated_data)
        membership = Membership.objects.create(
            user=user,
            company=company,
            status=Membership.Status.ACTIVE,
            is_primary=True,
            joined_at=timezone.now(),
        )
        roles = Role.objects.filter(code__in=role_codes, is_active=True)
        membership.roles.set(roles)
        AuditService.log(
            action="company.created",
            entity="company",
            entity_id=str(company.public_id),
            user=user,
            company=company,
            payload={
                "name": company.name,
                "slug": company.slug,
                "roles": list(roles.values_list("code", flat=True)),
            },
        )
        return company
