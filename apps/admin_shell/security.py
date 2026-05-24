from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from apps.access_control_center.services.smart_system_access import (
    filter_permissioned_items,
    get_default_company_for_user,
    get_smart_system_permission_map,
    has_smart_system_permission,
)
from apps.billing.services.billing_service import BillingAccessService
from apps.companies.services.tenant_scope import TenantScopeService
from apps.smart_system.services.tenant_scope import SmartSystemScopeService

from .services.shell import get_dashboard_context, get_navigation
from .services.tenant_scope import build_shell_tenant_context
from .services.client_portal import (
    build_client_portal_context,
    get_client_portal_navigation,
)


ACTION_LIST_KEYS = {"page_actions", "quick_actions", "action_panel", "shell_quick_actions"}


def filter_context_actions(payload, permission_map):
    if isinstance(payload, list):
        return [filter_context_actions(item, permission_map) for item in payload]
    if isinstance(payload, dict):
        filtered = {}
        for key, value in payload.items():
            if key in ACTION_LIST_KEYS and isinstance(value, list):
                filtered[key] = filter_permissioned_items(value, permission_map)
            elif isinstance(value, (dict, list)):
                filtered[key] = filter_context_actions(value, permission_map)
            else:
                filtered[key] = value
        return filtered
    return payload


class SmartSystemOperationalRouteMixin:
    """Rotas CMMS do Admin Shell: exige membership ativa em ao menos uma Company (usuario comum)."""

    enforce_active_company_membership = True


class SmartSystemAccessMixin(LoginRequiredMixin):
    login_url = "/admin/login/"
    permission_domain = None
    permission_action = "view"
    resource_type = ""
    denied_template_name = "admin_shell/access_denied.html"
    log_permission_decision = False
    enforce_billing_access = True

    enforce_active_company_membership = False

    def get_current_company(self):
        return TenantScopeService.resolve_context(self.request).company or get_default_company_for_user(self.request.user)

    def get_current_site(self):
        return TenantScopeService.resolve_context(self.request).site

    def get_permission_map(self):
        if not hasattr(self, "_smart_system_permission_map"):
            self._smart_system_permission_map = get_smart_system_permission_map(
                self.request.user,
                company=self.get_current_company(),
            )
        return self._smart_system_permission_map

    def get_permission_resource_id(self):
        for key in (
            "asset_code",
            "order_code",
            "plan_code",
            "failure_code",
            "checklist_code",
            "routine_code",
            "company_id",
            "part_code",
            "quote_number",
            "contract_number",
            "report_type",
        ):
            value = self.kwargs.get(key)
            if value:
                return str(value)
        return ""

    def has_required_permission(self):
        if not self.permission_domain:
            return True
        return has_smart_system_permission(
            self.request.user,
            self.permission_domain,
            self.permission_action,
            company=self.get_current_company(),
            log_decision=self.log_permission_decision,
            resource_type=self.resource_type or self.permission_domain,
            resource_id=self.get_permission_resource_id(),
            reason=f"{self.permission_domain}.{self.permission_action}",
        )

    def _maybe_deny_without_smart_system_company_membership(self, request):
        active = getattr(self, "enforce_active_company_membership", False)
        if not active:
            return None
        if not request.user.is_authenticated:
            return None
        if request.user.is_superuser:
            return None
        if SmartSystemScopeService.get_allowed_company_ids(request.user):
            return None
        return render(
            request,
            self.denied_template_name,
            self.get_access_denied_context(
                title="Nenhuma empresa vinculada",
                description=(
                    "Sua conta nao possui membership ativa em nenhuma empresa do Smart360. "
                    "Finalize o cadastro empresarial ou solicite um convite ao administrador para acessar o CMMS."
                ),
                notification_title="Contexto corporativo obrigatorio para esta area",
            ),
            status=403,
        )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        denial = self._maybe_deny_without_smart_system_company_membership(request)
        if denial is not None:
            return denial
        if self.enforce_billing_access:
            company_access = BillingAccessService.get_company_billing_context(self.get_current_company())
            if (
                company_access["company"] is not None
                and not company_access["access_allowed"]
                and not request.user.is_superuser
            ):
                return self.handle_subscription_blocked(company_access)
        if not self.has_required_permission():
            return self.handle_access_denied()
        return super().dispatch(request, *args, **kwargs)

    def get_access_denied_context(
        self,
        *,
        title="Acesso negado",
        description="Seu perfil atual nao possui permissao para executar esta acao no Smart System.",
        notification_title="Permissao insuficiente para a acao solicitada",
    ):
        permission_map = self.get_permission_map()
        user = self.request.user
        if self.permission_domain == "billing_admin":
            current_slug = "billing"
        elif self.permission_domain == "analytics_admin":
            current_slug = "analytics-platform"
        elif self.permission_domain and self.permission_domain.startswith("marketplace_"):
            current_slug = "marketplace-technicians"
        else:
            current_slug = "smart-system"
        return {
            "page_title": title,
            "page_description": description,
            "breadcrumbs": [
                {"label": "Dashboard", "url": "admin-shell:dashboard"},
                {"label": title, "url": None},
            ],
            "current_module_slug": current_slug,
            "shell_navigation": get_navigation(
                getattr(getattr(self.request, "resolver_match", None), "view_name", ""),
                current_slug,
                permission_map=permission_map,
            ),
            "shell_user": {
                "name": user.display_name or user.full_name or user.email,
                "email": user.email,
                "initials": "".join(part[0] for part in (user.first_name, user.last_name) if part).upper()[:2] or "S",
            },
            "shell_notifications": [
                {"title": notification_title, "time": "agora"},
            ],
            "shell_quick_actions": filter_permissioned_items(get_dashboard_context()["quick_actions"], permission_map),
            "shell_tenant_context": build_shell_tenant_context(self.request),
        }

    def handle_access_denied(self):
        return render(
            self.request,
            self.denied_template_name,
            self.get_access_denied_context(),
            status=403,
        )

    def handle_scope_denied(self):
        return render(
            self.request,
            self.denied_template_name,
            self.get_access_denied_context(
                title="Fora do escopo",
                description="O recurso solicitado existe, mas nao pertence a empresa ou unidade operacional autorizada para o seu contexto atual.",
                notification_title="Tentativa de acesso fora do escopo ativo",
            ),
            status=403,
        )

    def handle_context_required(self):
        return render(
            self.request,
            self.denied_template_name,
            self.get_access_denied_context(
                title="Contexto de empresa obrigatorio",
                description=(
                    "Selecione uma empresa ativa antes de gerar agenda, roteirizacao ou distribuir visitas. "
                    "Esse fluxo exige escopo operacional explicito para evitar planejamento cross-tenant."
                ),
                notification_title="Selecione uma empresa para continuar",
            ),
            status=403,
        )

    def handle_subscription_blocked(self, company_access):
        return render(
            self.request,
            self.denied_template_name,
            self.get_access_denied_context(
                title="Acesso bloqueado por assinatura",
                description=(
                    f"A empresa {company_access['company'].name} esta com acesso operacional bloqueado "
                    f"por status financeiro {company_access['access_status']}."
                ),
                notification_title="Assinatura bloqueada para o tenant ativo",
            ),
            status=402,
        )


class SmartSystemShellAccessMixin(SmartSystemAccessMixin):
    def get_shell_context(self):
        permission_map = self.get_permission_map()
        current_name = getattr(getattr(self.request, "resolver_match", None), "view_name", "")
        current_module_slug = self.kwargs.get("module_slug", "")
        user = self.request.user
        return {
            "shell_navigation": get_navigation(
                current_name,
                current_module_slug,
                permission_map=permission_map,
            ),
            "shell_user": {
                "name": user.display_name or user.full_name or user.email,
                "email": user.email,
                "initials": "".join(part[0] for part in (user.first_name, user.last_name) if part).upper()[:2] or "S",
            },
            "shell_notifications": [
                {"title": "4 incidentes tecnicos exigem revisao", "time": "agora"},
                {"title": "2 invoices vencem nas proximas 24h", "time": "12 min"},
                {"title": "Worker de analytics voltou ao estado saudavel", "time": "31 min"},
            ],
            "shell_quick_actions": filter_permissioned_items(get_dashboard_context()["quick_actions"], permission_map),
            "shell_tenant_context": build_shell_tenant_context(self.request),
        }

    def render_to_response(self, context, **response_kwargs):
        context = filter_context_actions(context, self.get_permission_map())
        return super().render_to_response(context, **response_kwargs)


class ClientPortalAccessMixin(SmartSystemAccessMixin):
    denied_template_name = "client_portal/access_denied.html"

    def get_access_denied_context(
        self,
        *,
        title="Acesso negado",
        description="Seu perfil atual nao possui permissao para executar esta acao no Portal do Cliente.",
        notification_title="Permissao insuficiente para a acao solicitada",
    ):
        permission_map = self.get_permission_map()
        context = build_client_portal_context(
            self.request,
            build_shell_tenant_context(self.request),
            permission_map,
        )
        context.update(
            {
                "page_title": title,
                "page_description": description,
                "breadcrumbs": [
                    {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
                    {"label": title, "url": None},
                ],
                "current_portal_section": "",
                "portal_navigation": get_client_portal_navigation(
                    getattr(getattr(self.request, "resolver_match", None), "view_name", ""),
                    permission_map=permission_map,
                ),
                "portal_notifications": [{"title": notification_title}],
            }
        )
        return context

    def dispatch(self, request, *args, **kwargs):
        permission_map = self.get_permission_map()
        has_portal_access = any(
            key.startswith("client_portal_") and bool(value)
            for key, value in permission_map.items()
        )
        if not request.user.is_superuser and not has_portal_access:
            return self.handle_access_denied()
        return super().dispatch(request, *args, **kwargs)


class ClientPortalShellAccessMixin(ClientPortalAccessMixin):
    def get_portal_context(self):
        return build_client_portal_context(
            self.request,
            build_shell_tenant_context(self.request),
            self.get_permission_map(),
        )

    def render_to_response(self, context, **response_kwargs):
        context = filter_context_actions(context, self.get_permission_map())
        return super().render_to_response(context, **response_kwargs)
