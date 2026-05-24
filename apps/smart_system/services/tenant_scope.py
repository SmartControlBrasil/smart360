from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Model, QuerySet

from apps.companies.models import Company, Membership, SiteMembership
from apps.companies.services.tenant_scope import TenantScopeService
from apps.smart_system.models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    Checklist,
    ChecklistItem,
    ContractAsset,
    CustomerEquipment,
    EquipmentModel,
    EquipmentModelPart,
    FieldExecutionSnapshot,
    FieldSyncOperation,
    FailureEvent,
    InspectionDivision,
    InspectionDivisionEquipment,
    MaintenanceContract,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    Part,
    PartAssetLink,
    PreventiveInspectionRoutine,
    QuoteItem,
    ClientPortalRequest,
    RoutePlan,
    ScheduledVisit,
    ServiceQuote,
    ServiceSignature,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
    WorkLog,
)


@dataclass(frozen=True)
class SmartSystemScope:
    company: Company | None
    site: OperationalSite | None
    company_ids: tuple[int, ...]
    site_ids: tuple[int, ...]
    restricted_to_sites: bool


class SmartSystemScopeService:
    COMPANY_FIELD_MAP = {
        MaintenanceClient: "company",
        OperationalSite: "maintenance_client__company",
        Asset: "operational_site__maintenance_client__company",
        EquipmentModel: "company",
        EquipmentModelPart: "company",
        CustomerEquipment: "company",
        Checklist: "company",
        ChecklistItem: "checklist__company",
        MaintenancePlan: "company",
        MaintenanceContract: "company",
        PreventiveInspectionRoutine: "company",
        InspectionDivision: "routine__company",
        InspectionDivisionEquipment: "division__routine__company",
        ContractAsset: "contract__company",
        ServiceOrder: "client__company",
        ServiceOrderChecklistResponse: "service_order__client__company",
        FailureEvent: "asset__operational_site__maintenance_client__company",
        AssetHistoryEvent: "asset__operational_site__maintenance_client__company",
        WorkLog: "service_order__client__company",
        ServiceDocument: "service_order__client__company",
        Part: "company",
        PartAssetLink: "part__company",
        ServiceQuote: "company",
        QuoteItem: "quote__company",
        StockMovement: "company",
        ClientPortalRequest: "company",
        ServiceSignature: "company",
        FieldExecutionSnapshot: "company",
        FieldSyncOperation: "company",
        TechnicianAvailabilityWindow: "company",
        TechnicianSchedule: "company",
        RoutePlan: "company",
        ScheduledVisit: "company",
    }

    SITE_FIELD_MAP = {
        OperationalSite: "id",
        Asset: "operational_site",
        EquipmentModel: None,
        EquipmentModelPart: None,
        CustomerEquipment: "site",
        Checklist: "operational_site",
        ChecklistItem: "checklist__operational_site",
        MaintenancePlan: "operational_site",
        MaintenanceContract: "operational_site",
        PreventiveInspectionRoutine: "operational_site",
        InspectionDivision: "routine__operational_site",
        InspectionDivisionEquipment: "division__routine__operational_site",
        ContractAsset: "asset__operational_site",
        ServiceOrder: "operational_site",
        ServiceOrderChecklistResponse: "service_order__operational_site",
        FailureEvent: "asset__operational_site",
        AssetHistoryEvent: "asset__operational_site",
        WorkLog: "service_order__operational_site",
        ServiceDocument: "service_order__operational_site",
        Part: "operational_site",
        PartAssetLink: "asset__operational_site",
        ServiceQuote: "operational_site",
        QuoteItem: "quote__operational_site",
        StockMovement: "operational_site",
        ClientPortalRequest: "operational_site",
        ServiceSignature: "operational_site",
        FieldExecutionSnapshot: "operational_site",
        FieldSyncOperation: "operational_site",
        TechnicianAvailabilityWindow: "operational_site",
        TechnicianSchedule: "operational_site",
        RoutePlan: "operational_site",
        ScheduledVisit: "operational_site",
    }

    @classmethod
    def get_allowed_company_ids(cls, user) -> list[int]:
        if not getattr(user, "is_authenticated", False):
            return []
        if getattr(user, "is_superuser", False):
            return list(Company.objects.values_list("id", flat=True))
        return list(
            Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            .values_list("company_id", flat=True)
            .distinct()
        )

    @classmethod
    def get_allowed_site_ids(cls, user, company_ids: list[int] | None = None) -> list[int]:
        if not getattr(user, "is_authenticated", False):
            return []
        if getattr(user, "is_superuser", False):
            queryset = OperationalSite.objects.all()
            if company_ids:
                queryset = queryset.filter(maintenance_client__company_id__in=company_ids)
            return list(queryset.values_list("id", flat=True))

        memberships = SiteMembership.objects.filter(user=user, status=SiteMembership.Status.ACTIVE)
        if company_ids:
            memberships = memberships.filter(company_id__in=company_ids)
        return list(memberships.values_list("site_id", flat=True).distinct())

    @classmethod
    def resolve_scope(cls, request) -> SmartSystemScope:
        tenant_context = TenantScopeService.resolve_context(request)
        company_ids = cls.get_allowed_company_ids(request.user)
        site_ids = cls.get_allowed_site_ids(request.user, company_ids)
        restricted_to_sites = bool(site_ids)

        return SmartSystemScope(
            company=tenant_context.company,
            site=tenant_context.site,
            company_ids=tuple(company_ids),
            site_ids=tuple(site_ids),
            restricted_to_sites=restricted_to_sites,
        )

    @classmethod
    def scope_queryset(cls, queryset: QuerySet, request) -> QuerySet:
        model = queryset.model
        scope = cls.resolve_scope(request)
        company_field = cls.COMPANY_FIELD_MAP.get(model)
        site_field = cls.SITE_FIELD_MAP.get(model)

        if company_field and scope.company_ids:
            queryset = queryset.filter(**{f"{company_field}_id__in": scope.company_ids})
        elif company_field:
            return queryset.none()

        if scope.company and company_field:
            queryset = queryset.filter(**{f"{company_field}_id": scope.company.id})

        if site_field and scope.restricted_to_sites:
            queryset = queryset.filter(**{f"{site_field}_id__in": scope.site_ids})
        if site_field and scope.site:
            queryset = queryset.filter(**{f"{site_field}_id": scope.site.id})

        return queryset.distinct()

    @classmethod
    def scope_related_queryset(cls, model: type[Model], request):
        base_queryset = model.objects.all()
        if model is AssetCategory:
            return base_queryset
        return cls.scope_queryset(base_queryset, request)

    @classmethod
    def user_can_access_company(cls, user, company) -> bool:
        return TenantScopeService.user_can_access_company(user, company)

    @classmethod
    def user_can_access_site(cls, user, site) -> bool:
        return TenantScopeService.user_can_access_site(user, site)

    @classmethod
    def object_in_scope(cls, request, *, company=None, site=None) -> bool:
        scope = cls.resolve_scope(request)
        if company and company.id not in scope.company_ids:
            return False
        if scope.company and company and scope.company.id != company.id:
            return False
        if site:
            if scope.restricted_to_sites and site.id not in scope.site_ids:
                return False
            if scope.site and scope.site.id != site.id:
                return False
        return True
