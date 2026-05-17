from __future__ import annotations

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied

from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import (
    Asset,
    Checklist,
    ChecklistItem,
    FailureEvent,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    Part,
    PartAssetLink,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
    WorkLog,
)
from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
)


@dataclass(frozen=True)
class PublicApiScope:
    company: Company | None
    site: OperationalSite | None
    companies: list
    sites: list


class PublicApiScopeService:
    @staticmethod
    def _get_integration_credential(request):
        return getattr(request, "integration_credential", None)

    COMPANY_FIELD_MAP = {
        MaintenanceClient: "company",
        OperationalSite: "maintenance_client__company",
        Asset: "operational_site__maintenance_client__company",
        Checklist: "company",
        ChecklistItem: "checklist__company",
        MaintenancePlan: "company",
        ServiceOrder: "client__company",
        ServiceOrderChecklistResponse: "service_order__client__company",
        FailureEvent: "asset__operational_site__maintenance_client__company",
        WorkLog: "service_order__client__company",
        ServiceDocument: "service_order__client__company",
        Part: "company",
        PartAssetLink: "part__company",
        StockMovement: "company",
        TechnicianProfile: "company",
        TechnicianServiceRequest: "requester_company",
        TechnicianServiceOffer: "service_request__requester_company",
        TechnicianAssignment: "technician_service_request__requester_company",
        TechnicianReview: "reviewer_company",
    }

    SITE_FIELD_MAP = {
        OperationalSite: "id",
        Asset: "operational_site",
        Checklist: "operational_site",
        ChecklistItem: "checklist__operational_site",
        MaintenancePlan: "operational_site",
        ServiceOrder: "operational_site",
        ServiceOrderChecklistResponse: "service_order__operational_site",
        FailureEvent: "asset__operational_site",
        WorkLog: "service_order__operational_site",
        ServiceDocument: "service_order__operational_site",
        Part: "operational_site",
        PartAssetLink: "asset__operational_site",
        StockMovement: "operational_site",
        TechnicianServiceRequest: "related_site",
        TechnicianServiceOffer: "service_request__related_site",
        TechnicianAssignment: "technician_service_request__related_site",
        TechnicianReview: "assignment__technician_service_request__related_site",
    }

    @classmethod
    def get_allowed_companies(cls, user):
        if not getattr(user, "is_authenticated", False):
            return []
        request = getattr(user, "_public_api_request", None)
        credential = cls._get_integration_credential(request) if request is not None else None
        if getattr(user, "is_superuser", False):
            queryset = Company.objects.filter(status=Company.Status.ACTIVE).order_by("name")
            if credential and credential.company_id:
                queryset = queryset.filter(id=credential.company_id)
            return list(queryset)
        memberships = (
            Membership.objects.select_related("company")
            .filter(user=user, status=Membership.Status.ACTIVE, company__status=Company.Status.ACTIVE)
            .order_by("-is_primary", "company__name")
        )
        companies = [membership.company for membership in memberships]
        if credential and credential.company_id:
            companies = [company for company in companies if company.id == credential.company_id]
        return companies

    @classmethod
    def get_allowed_sites(cls, user, company=None):
        if not getattr(user, "is_authenticated", False):
            return []
        request = getattr(user, "_public_api_request", None)
        credential = cls._get_integration_credential(request) if request is not None else None
        if getattr(user, "is_superuser", False):
            queryset = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
            if company is not None:
                queryset = queryset.filter(maintenance_client__company=company)
            if credential and credential.company_id:
                queryset = queryset.filter(maintenance_client__company_id=credential.company_id)
            return list(queryset.order_by("name"))

        memberships = (
            SiteMembership.objects.select_related("site", "site__maintenance_client", "site__maintenance_client__company")
            .filter(user=user, status=SiteMembership.Status.ACTIVE, site__is_active=True)
            .order_by("-is_primary", "site__name")
        )
        if company is not None:
            memberships = memberships.filter(company=company)
        if credential and credential.company_id:
            memberships = memberships.filter(company_id=credential.company_id)
        return [membership.site for membership in memberships]

    @classmethod
    def resolve_scope(cls, request) -> PublicApiScope:
        setattr(request.user, "_public_api_request", request)
        companies = cls.get_allowed_companies(request.user)
        company_slug = request.headers.get("X-Company-Slug") or request.query_params.get("company")
        requested_site_code = request.headers.get("X-Site-Code") or request.query_params.get("site")

        active_company = None
        if companies:
            if company_slug:
                active_company = next((item for item in companies if item.slug == company_slug), None)
                if active_company is None:
                    raise PermissionDenied("Requested company is outside the authenticated scope.")
            else:
                active_company = companies[0]

        sites = cls.get_allowed_sites(request.user, company=active_company)
        active_site = None
        if requested_site_code:
            active_site = next((item for item in sites if item.code == requested_site_code), None)
            if active_site is None:
                raise PermissionDenied("Requested site is outside the authenticated scope.")

        return PublicApiScope(
            company=active_company,
            site=active_site,
            companies=companies,
            sites=sites,
        )

    @classmethod
    def scope_queryset(cls, queryset, request):
        scope = cls.resolve_scope(request)
        company_field = cls.COMPANY_FIELD_MAP.get(queryset.model)
        site_field = cls.SITE_FIELD_MAP.get(queryset.model)

        if company_field:
            company_ids = [company.id for company in scope.companies]
            if not company_ids:
                return queryset.none()
            queryset = queryset.filter(**{f"{company_field}_id__in": company_ids})
            if scope.company is not None:
                queryset = queryset.filter(**{f"{company_field}_id": scope.company.id})

        if site_field:
            site_ids = [site.id for site in scope.sites]
            if site_ids:
                queryset = queryset.filter(**{f"{site_field}_id__in": site_ids})
            if scope.site is not None:
                queryset = queryset.filter(**{f"{site_field}_id": scope.site.id})

        return queryset.distinct()
