from __future__ import annotations

from apps.companies.services.tenant_scope import TenantScopeService


def build_shell_tenant_context(request):
    context = TenantScopeService.resolve_context(request)
    available_companies = TenantScopeService.get_available_companies(request.user)
    available_sites = TenantScopeService.get_available_sites(request.user, company=context.company)
    return {
        "company": context.company,
        "site": context.site,
        "company_options": [
            {"id": company.id, "label": company.name, "slug": company.slug}
            for company in available_companies
        ],
        "site_options": [
            {"id": site.id, "label": site.name, "code": site.code}
            for site in available_sites
        ],
    }


def apply_active_scope_filters(filters, tenant_context):
    scoped_filters = dict(filters or {})
    if tenant_context.get("company") and not scoped_filters.get("client"):
        scoped_filters["client"] = tenant_context["company"].name
    if tenant_context.get("site") and not scoped_filters.get("site"):
        scoped_filters["site"] = tenant_context["site"].name
    return scoped_filters


def record_matches_scope(record, tenant_context, client_key="client", site_key="site"):
    active_company = tenant_context.get("company")
    active_site = tenant_context.get("site")
    if active_company and record.get(client_key) not in {active_company.name, getattr(active_company, "legal_name", "")}:
        return False
    if active_site and record.get(site_key) != active_site.name:
        return False
    return True


def filter_records_for_scope(records, tenant_context, client_key="client", site_key="site"):
    return [record for record in records if record_matches_scope(record, tenant_context, client_key=client_key, site_key=site_key)]
