from __future__ import annotations

from dataclasses import dataclass

from apps.companies.models import Membership, SiteMembership


@dataclass
class TenantContext:
    company: object | None
    site: object | None
    available_companies: list
    available_sites: list
    scope_mode: str = "all-sites"

    @property
    def company_slug(self):
        return getattr(self.company, "slug", "")

    @property
    def site_code(self):
        return getattr(self.site, "code", "")


class TenantScopeService:
    COMPANY_SESSION_KEY = "smart_system_active_company_id"
    SITE_SESSION_KEY = "smart_system_active_site_id"

    @classmethod
    def get_available_companies(cls, user):
        if not getattr(user, "is_authenticated", False):
            return []
        if getattr(user, "is_superuser", False):
            from apps.companies.models import Company

            return list(Company.objects.filter(status=Company.Status.ACTIVE).order_by("name"))
        memberships = (
            Membership.objects.select_related("company")
            .filter(user=user, status=Membership.Status.ACTIVE, company__status="active")
            .order_by("-is_primary", "company__name")
        )
        return [membership.company for membership in memberships]

    @classmethod
    def get_available_sites(cls, user, company=None):
        if not getattr(user, "is_authenticated", False):
            return []
        if getattr(user, "is_superuser", False):
            from apps.smart_system.models import OperationalSite

            queryset = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
            if company is not None:
                queryset = queryset.filter(maintenance_client__company=company)
            return list(queryset.order_by("maintenance_client__display_name", "name"))
        memberships = (
            SiteMembership.objects.select_related("site", "site__maintenance_client", "site__maintenance_client__company")
            .filter(user=user, status=SiteMembership.Status.ACTIVE, site__is_active=True)
            .order_by("-is_primary", "site__name")
        )
        if company is not None:
            memberships = memberships.filter(company=company)
        return [membership.site for membership in memberships]

    @classmethod
    def resolve_context(cls, request):
        user = request.user
        companies = cls.get_available_companies(user)
        active_company = None
        if companies:
            requested_company_id = request.session.get(cls.COMPANY_SESSION_KEY)
            active_company = next((company for company in companies if company.id == requested_company_id), companies[0])
            request.session[cls.COMPANY_SESSION_KEY] = active_company.id
        sites = cls.get_available_sites(user, company=active_company)
        requested_site_id = request.session.get(cls.SITE_SESSION_KEY)
        active_site = next((site for site in sites if site.id == requested_site_id), None)
        if active_site:
            request.session[cls.SITE_SESSION_KEY] = active_site.id
        else:
            request.session.pop(cls.SITE_SESSION_KEY, None)
        return TenantContext(
            company=active_company,
            site=active_site,
            available_companies=companies,
            available_sites=sites,
            scope_mode="single-site" if active_site else "all-sites",
        )

    @classmethod
    def set_active_context(cls, request, company_id=None, site_id=None):
        companies = cls.get_available_companies(request.user)
        if company_id:
            company = next((item for item in companies if item.id == company_id), None)
            if company is not None:
                request.session[cls.COMPANY_SESSION_KEY] = company.id
        context = cls.resolve_context(request)
        if site_id == "all":
            request.session.pop(cls.SITE_SESSION_KEY, None)
        elif site_id:
            try:
                site_id = int(site_id)
            except (TypeError, ValueError):
                site_id = None
            if site_id:
                site = next((item for item in context.available_sites if item.id == site_id), None)
                if site is not None:
                    request.session[cls.SITE_SESSION_KEY] = site.id
        return cls.resolve_context(request)

    @classmethod
    def user_can_access_company(cls, user, company):
        if getattr(user, "is_superuser", False):
            return True
        return Membership.objects.filter(user=user, company=company, status=Membership.Status.ACTIVE).exists()

    @classmethod
    def user_can_access_site(cls, user, site):
        if getattr(user, "is_superuser", False):
            return True
        return SiteMembership.objects.filter(user=user, site=site, status=SiteMembership.Status.ACTIVE).exists()
