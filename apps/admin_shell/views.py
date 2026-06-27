import json

from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views import View
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.utils import timezone
from django.db.models import Q

from apps.access_control_center.services.access_service import AccessAuditService
from apps.ai_agents_center.models import AIBriefing, AgentActionProposal
from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.ai_agents_center.services.client_portal_copilot import ClientPortalCopilotService
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.analytics_platform.models import OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.billing.models import Contract, Invoice
from apps.billing.services.billing_service import ContractService, PaymentService
from apps.companies.models import Membership, SiteMembership
from apps.companies.services.company_shell_access import user_can_create_saas_company
from apps.companies.services.tenant_scope import TenantScopeService
from apps.integration_bus.services.realtime_bus import RealtimeEventBus

from .forms import (
    CLIENT_PORTAL_GROUP_DESCRIPTIONS,
    CLIENT_PORTAL_GROUP_LABELS,
    ClientPortalRequestForm,
    ClientPortalUserForm,
    ClientQuoteDecisionForm,
    ClientServiceSignatureForm,
    CorrectiveServiceOrderForm,
    PreventiveServiceOrderForm,
    SmartSystemMaintenanceClientForm,
    SmartSystemOperationalSiteForm,
    SmartSystemChecklistForm,
    SmartSystemChecklistItemForm,
    SmartSystemPartForm,
    SmartSystemCustomerEquipmentForm,
    SmartSystemEquipmentModelForm,
    TechnicianServiceSignatureForm,
)
from .security import (
    ClientPortalAccessMixin,
    ClientPortalShellAccessMixin,
    SmartSystemAccessMixin,
    SmartSystemOperationalRouteMixin,
    SmartSystemShellAccessMixin,
)
from .services.client_portal import (
    create_client_portal_request,
    generate_client_report_pdf,
    get_client_asset_detail_context,
    get_client_asset_listing_context,
    get_client_contract_detail_context,
    get_client_contract_listing_context,
    get_client_dashboard_context,
    get_client_preventive_detail_context,
    get_client_preventive_listing_context,
    get_client_profile_context,
    get_client_quote_detail_context,
    get_client_quote_listing_context,
    get_client_report_listing_context,
    get_client_report_preview,
    get_client_request_detail_context,
    get_client_request_listing_context,
    get_client_site_listing_context,
    get_client_work_order_detail_context,
    get_client_work_order_listing_context,
)
from .services.billing import (
    get_billing_contract_context,
    get_billing_dashboard_context,
    get_billing_invoice_context,
    get_billing_plan_context,
    get_contract_detail_context,
)
from .services.analytics_executive import get_analytics_executive_context
from .services.ai_digital_twin import get_ai_digital_twin_context
from .services.ai_knowledge_graph import get_ai_knowledge_graph_context
from .services.ai_voice_ops import get_ai_voiceops_context
from .services.executive_war_room import build_executive_war_room_context
from .services.ai_agents_center import (
    get_ai_agents_anomaly_health_context,
    get_ai_autonomy_center_context,
    get_ai_agents_dashboard_context,
    get_ai_experimentation_center_context,
    get_ai_manager_copilot_context,
    get_ai_agents_maintenance_health_context,
    get_ai_agents_marketplace_health_context,
    get_ai_optimization_center_context,
    get_ai_policy_studio_context,
    get_ai_agents_profitability_health_context,
    get_ai_decision_center_context,
    get_ai_simulation_center_context,
    get_ai_agents_proposals_context,
    get_ai_agents_recommendations_context,
    get_ai_agents_runs_context,
    get_ai_briefings_context,
    get_ai_agents_scheduling_health_context,
    get_operations_health_context,
)
from .services.observability import get_observability_dashboard_context
from .services.marketplace_technicians import (
    get_assignment_listing_context,
    get_matching_listing_context,
    get_marketplace_dashboard_context,
    get_review_listing_context,
    get_service_offer_listing_context,
    get_service_request_listing_context,
    get_technician_detail_context,
    get_technician_listing_context,
)
from .services.shell import MODULE_PAGES, build_module_page_context, get_dashboard_context, get_smart_system_dashboard_context
from .services.smart_system_assets import get_asset_detail_context, get_asset_listing_context
from .services.smart_system_customer_equipments import (
    get_customer_equipment_detail_context,
    get_customer_equipment_listing_context,
)
from .services.smart_system_customers import (
    get_customer_detail_context,
    get_customer_listing_context,
)
from .services.smart_system_equipment_models import (
    get_equipment_model_detail_context,
    get_equipment_model_listing_context,
)
from .services.smart_system_checklists import (
    get_checklist_detail_context,
    get_checklist_listing_context,
    get_execution_context,
)
from .services.smart_system_failures import get_failure_detail_context, get_failure_listing_context
from .services.smart_system_parts import get_part_detail_context, get_part_listing_context, get_stock_movement_context
from .services.smart_system_contracts import get_contract_detail_context, get_contract_listing_context
from .services.smart_system_quotes import get_quote_detail_context, get_quote_listing_context
from .services.smart_system_preventives import (
    get_preventive_calendar_context,
    get_preventive_detail_context,
    get_preventive_listing_context,
    get_preventive_schedule_context,
)
from .services.smart_system_reports import (
    generate_report_pdf,
    get_report_listing_context,
    get_report_preview_context,
)
from .services.smart_system_scheduling import (
    get_schedule_calendar_context,
    get_scheduling_dashboard_context,
    get_technician_agenda_context,
    get_technician_mobile_schedule_context,
    get_unassigned_visits_context,
)
from .services.smart_system_work_order_mutations import (
    post_service_order_checklist_responses,
    post_service_order_complete,
    post_service_order_named_transition,
    post_service_order_progress_notes,
    post_service_order_transition,
    post_service_order_worklog,
)
from .services.smart_system_work_order_create import (
    build_corrective_work_order_create_context,
    build_preventive_work_order_create_context,
    maintenance_plan_client_and_site,
    scoped_assets_for_corrective_order,
)
from .services.smart_system_work_order_execution import get_work_order_execution_context
from .services.smart_system_work_orders import get_work_order_detail_context, get_work_order_listing_context
from apps.smart_system.models import Checklist, ChecklistItem, ServiceOrder, ServiceSignature
from apps.smart_system.models import CustomerEquipment, EquipmentModel, MaintenanceClient, OperationalSite
from apps.smart_system.services.maintenance_service import ServiceOrderService
from apps.smart_system.services.admin_shell_dashboard import build_operations_chart_data
from apps.smart_system.services.tenant_scope import SmartSystemScopeService
from apps.smart_system.services.offline_sync import FieldOfflineSyncService
from apps.smart_system.services.quote_service import ServiceQuoteService
from apps.smart_system.services.maintenance_contract_service import MaintenanceContractService
from apps.smart_system.services.signature_service import ServiceSignatureService
from .services.tenant_scope import apply_active_scope_filters, build_shell_tenant_context
from .services.technician_mobile import (
    build_technician_app_context,
    get_technician_copilot_bootstrap,
    get_technician_checklist_listing_context,
    get_technician_dashboard_context,
    get_technician_execution_context,
    get_technician_history_context,
    get_technician_offline_bundle_context,
    get_technician_profile_context,
    get_technician_service_detail_context,
    get_technician_service_listing_context,
)
from apps.ai_agents_center.services.technician_copilot import TechnicianCopilotService


class ShellContextMixin(SmartSystemShellAccessMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_shell_context())
        return context

    def get_tenant_context(self):
        return self.get_shell_context()["shell_tenant_context"]

    def require_active_company_context(self):
        tenant_context = self.get_tenant_context()
        if tenant_context.get("company") is None and not self.request.user.is_superuser:
            return self.handle_context_required()
        return None

    # Global form invalid handler for all Shell FormViews.
    def form_invalid(self, form):
        """
        Ensure consistent behavior on form validation errors:
        - stay on the same page
        - preserve submitted data (form instance provided to template)
        - show a global error message
        - render with HTTP 400 so monitoring can pick up client errors
        """
        from django.shortcuts import render

        messages.error(self.request, "Não foi possível salvar. Verifique os campos destacados.")
        # ensure form is available in context for templates expecting it
        context = self.get_context_data(form=form)
        # When using FormView, render the template with status 400
        return render(self.request, self.get_template_names(), context=context, status=400)


class ClientPortalUserAdminMixin(ShellContextMixin):
    permission_domain = "users"
    permission_action = "manage"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_module_slug": "core-platform",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Usuários do Portal", "url": "admin-shell:client-portal-users"},
                ],
            }
        )
        return context


class ClientPortalUserListView(ClientPortalUserAdminMixin, TemplateView):
    template_name = "admin_shell/client_portal_users/list.html"

    @staticmethod
    def _client_portal_users_queryset():
        return (
            get_user_model()
            .objects.filter(Q(user_type="client") | Q(groups__name="client-portal-only"))
            .prefetch_related("groups")
            .distinct()
            .order_by("email")
        )

    @staticmethod
    def _access_label(user):
        names = set(user.groups.values_list("name", flat=True))
        for group_name, label in CLIENT_PORTAL_GROUP_LABELS.items():
            if group_name in names:
                return label
        return CLIENT_PORTAL_GROUP_LABELS["client-portal-only"]

    @staticmethod
    def _last_login(user):
        return getattr(user, "last_login_at", None) or getattr(user, "last_login", None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = list(self._client_portal_users_queryset())
        memberships = {}
        for membership in (
            Membership.objects.filter(
                user_id__in=[user.id for user in users],
                status=Membership.Status.ACTIVE,
            )
            .select_related("company")
            .order_by("user_id", "-is_primary", "company__name")
        ):
            memberships.setdefault(membership.user_id, membership)
        site_memberships = {}
        for site_membership in (
            SiteMembership.objects.filter(
                user_id__in=[user.id for user in users],
                status=SiteMembership.Status.ACTIVE,
            )
            .select_related("site", "company")
            .order_by("user_id", "-is_primary", "site__name")
        ):
            site_memberships.setdefault(site_membership.user_id, site_membership)
        rows = []
        for user in users:
            membership = memberships.get(user.id)
            site_membership = site_memberships.get(user.id)
            rows.append(
                {
                    "user": user,
                    "company": membership.company if membership else None,
                    "site": site_membership.site if site_membership else None,
                    "access_level": self._access_label(user),
                    "last_login": self._last_login(user),
                }
            )
        context.update(
            {
                "page_title": "Usuários do Portal",
                "page_description": (
                    "Usuários do Portal acessam somente o painel básico em /portal/ para abrir e acompanhar chamados. "
                    "Eles não acessam o painel interno do Smart360."
                ),
                "portal_user_rows": rows,
                "create_url": reverse("admin-shell:client-portal-user-create"),
            }
        )
        return context


class ClientPortalUserCreateView(ClientPortalUserAdminMixin, FormView):
    template_name = "admin_shell/client_portal_users/form.html"
    form_class = ClientPortalUserForm

    def get_success_url(self):
        return reverse("admin-shell:client-portal-users")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_mode": "create",
                "page_title": "Novo usuário do Portal",
                "page_description": "Cadastre um login externo para acessar somente /portal/.",
                "access_descriptions": CLIENT_PORTAL_GROUP_DESCRIPTIONS,
                "cancel_href": reverse("admin-shell:client-portal-users"),
            }
        )
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Usuário do Portal criado com sucesso.")
        return super().form_valid(form)


class ClientPortalUserUpdateView(ClientPortalUserCreateView):
    form_mode = "update"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            get_user_model().objects.prefetch_related("groups"),
            pk=kwargs["user_id"],
        )
        if self.object.is_staff or self.object.is_superuser:
            raise Http404("Usuário interno não pode ser editado por esta tela.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_mode": "update",
                "page_title": "Editar usuário do Portal",
                "page_description": "Atualize empresa, unidade, status e nível de acesso do login externo.",
            }
        )
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Usuário do Portal atualizado com sucesso.")
        return FormView.form_valid(self, form)


class CMMSOperationalShellMixin(SmartSystemOperationalRouteMixin, ShellContextMixin):
    """Rotas CMMS no Admin Shell: shell + obrigatoriedade de membership empresa (usuario comum)."""


class ClientPortalContextMixin(ClientPortalShellAccessMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_portal_context())
        context["portal_copilot_entrypoint"] = self.build_portal_copilot_entrypoint()
        return context

    def get_tenant_context(self):
        return self.get_portal_context()["portal_tenant_context"]

    def build_portal_copilot_entrypoint(self):
        params = []
        question = ""
        if self.kwargs.get("asset_code"):
            params.append(f"asset={self.kwargs['asset_code']}")
            question = f"Explique o ativo {self.kwargs['asset_code']}."
        elif self.kwargs.get("order_code"):
            params.append(f"work_order={self.kwargs['order_code']}")
            question = f"Explique o status da OS {self.kwargs['order_code']}."
        elif self.kwargs.get("quote_number"):
            params.append(f"quote={self.kwargs['quote_number']}")
            question = f"Explique o orcamento {self.kwargs['quote_number']}."
        elif self.kwargs.get("contract_number"):
            params.append(f"contract={self.kwargs['contract_number']}")
            question = f"Resuma o contrato {self.kwargs['contract_number']}."
        elif self.kwargs.get("protocol_number"):
            params.append(f"request={self.kwargs['protocol_number']}")
            question = f"Explique a solicitacao {self.kwargs['protocol_number']}."
        elif self.kwargs.get("public_id"):
            params.append(f"preventive={self.kwargs['public_id']}")
            question = "Explique esta preventiva."
        elif self.kwargs.get("report_type") and self.kwargs.get("reference_code"):
            params.append(f"report_type={self.kwargs['report_type']}")
            params.append(f"reference_code={self.kwargs['reference_code']}")
            question = "Explique este relatorio de forma simples."
        if question:
            params.append(f"question={question}")
        base_url = reverse("admin-shell:client-portal-copilot")
        return f"{base_url}?{'&'.join(params)}" if params else base_url


class ClientPortalScopedResourceTemplateView(ClientPortalContextMixin, TemplateView):
    scoped_resource = None

    def load_scoped_resource(self):
        return None

    def get(self, request, *args, **kwargs):
        self.scoped_resource = self.load_scoped_resource()
        if self.scoped_resource is None:
            return self.handle_scope_denied()
        return super().get(request, *args, **kwargs)


class TechnicianAppContextMixin(SmartSystemShellAccessMixin):
    mobile_permission_domain = "work_orders"
    mobile_permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            build_technician_app_context(
                self.request,
                build_shell_tenant_context(self.request),
                self.get_permission_map(),
            )
        )
        return context

    def get_tenant_context(self):
        return build_shell_tenant_context(self.request)


class TechnicianScopedTemplateView(TechnicianAppContextMixin, TemplateView):
    scoped_resource = None

    def load_scoped_resource(self):
        return None

    def get(self, request, *args, **kwargs):
        self.scoped_resource = self.load_scoped_resource()
        if self.scoped_resource is None:
            return self.handle_scope_denied()
        return super().get(request, *args, **kwargs)


class ScopedResourceTemplateView(CMMSOperationalShellMixin, TemplateView):
    scoped_resource = None

    def load_scoped_resource(self):
        return None

    def get(self, request, *args, **kwargs):
        self.scoped_resource = self.load_scoped_resource()
        if self.scoped_resource is None:
            return self.handle_scope_denied()
        return super().get(request, *args, **kwargs)


class SetActiveContextView(SmartSystemShellAccessMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"

    def post(self, request):
        company_id = request.POST.get("company_id") or None
        raw_site_id = request.POST.get("site_id")
        site_id = raw_site_id if raw_site_id not in (None, "") else "all"
        TenantScopeService.set_active_context(
            request,
            company_id=int(company_id) if company_id else None,
            site_id=site_id,
        )
        return redirect(request.POST.get("next") or reverse("admin-shell:dashboard"))


class TechnicianLoginView(LoginView):
    template_name = "technician_pwa/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("admin-shell:technician-app-dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "SMART360 Field App"
        context["page_description"] = "Acesso rapido para atendimento tecnico, checklist e execucao em campo."
        return context


class TechnicianLogoutView(LogoutView):
    next_page = "/field/login/"


class TechnicianDashboardView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/dashboard.html"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_technician_dashboard_context(self.request.user, self.get_tenant_context()))
        context.update(get_technician_mobile_schedule_context(user=self.request.user, tenant_context=self.get_tenant_context()))
        context["offline_bootstrap"] = {
            "screen": "dashboard",
            "dashboard": context["dashboard_cards"],
            "today_services": context["today_services"],
            "alerts": context["operational_alerts"],
            "today_route": context["today_route_cards"],
        }
        context["page_title"] = "Inicio"
        context["page_description"] = "O que precisa ser atendido agora no campo."
        context["current_mobile_section"] = "home"
        context["latest_briefing"] = AIBriefingComposer.latest_for_context(
            company=self.get_tenant_context().get("company"),
            audience=AIBriefing.Audience.TECHNICIAN,
            user=self.request.user,
            site=self.get_tenant_context().get("site"),
        )
        return context


class TechnicianBriefingDetailView(TechnicianScopedTemplateView):
    template_name = "technician_pwa/briefing_detail.html"
    permission_domain = "dashboard"
    permission_action = "view"

    def load_scoped_resource(self):
        return AIBriefingComposer.list_accessible_briefings(
            user=self.request.user,
            company=self.get_tenant_context().get("company"),
            audience=AIBriefing.Audience.TECHNICIAN,
        ).filter(public_id=self.kwargs["briefing_id"]).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        briefing = self.scoped_resource
        AIBriefingComposer.mark_viewed(briefing=briefing, user=self.request.user)
        context["briefing"] = briefing
        context["page_title"] = briefing.title
        context["page_description"] = briefing.summary
        context["current_mobile_section"] = "home"
        return context


class TechnicianServiceListView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/services_list.html"
    permission_domain = "work_orders"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_technician_service_listing_context(self.request.user, self.get_tenant_context(), filters))
        context["offline_bootstrap"] = {
            "screen": "services",
            "filters": filters,
            "services": context["service_cards"],
        }
        context["page_title"] = "Servicos"
        context["page_description"] = "Carteira de ordens e atendimentos atribuidos."
        context["current_mobile_section"] = "services"
        return context


class TechnicianScheduleView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/schedule.html"
    permission_domain = "scheduling"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_technician_mobile_schedule_context(user=self.request.user, tenant_context=self.get_tenant_context()))
        context["offline_bootstrap"] = {
            "screen": "schedule",
            "today_route": context["today_route_cards"],
            "next_visit": context["next_visit"],
        }
        context["page_title"] = "Agenda"
        context["page_description"] = "Sequencia do dia, proxima visita e carga operacional em campo."
        context["current_mobile_section"] = "schedule"
        return context


class TechnicianServiceDetailView(TechnicianScopedTemplateView):
    template_name = "technician_pwa/service_detail.html"
    permission_domain = "work_orders"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_technician_service_detail_context(self.request.user, self.get_tenant_context(), self.kwargs["order_code"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["technician_copilot_bootstrap"] = get_technician_copilot_bootstrap(self.scoped_resource)
        context["offline_bootstrap"] = {
            "screen": "service_detail",
            "service": context["service"],
            "execution_summary": context["execution"]["summary_cards"],
            "timeline": context["execution"]["timeline"],
            "copilot": context["technician_copilot_bootstrap"],
        }
        context["page_title"] = self.scoped_resource["service"]["code"]
        context["page_description"] = self.scoped_resource["service"]["title"]
        context["current_mobile_section"] = "services"
        return context


class TechnicianExecutionView(TechnicianScopedTemplateView):
    template_name = "technician_pwa/execution.html"
    permission_domain = "work_execution"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_technician_execution_context(self.request.user, self.get_tenant_context(), self.kwargs["order_code"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["technician_copilot_bootstrap"] = get_technician_copilot_bootstrap(self.scoped_resource)
        context["technician_signature_form"] = TechnicianServiceSignatureForm(
            initial={"signer_name": self.request.user.display_name or self.request.user.full_name or self.request.user.email}
        )
        context["client_signature_form"] = ClientServiceSignatureForm()
        context["signature_error"] = self.request.GET.get("signature_error", "")
        context["offline_bootstrap"] = {
            "screen": "execution",
            "service": context["service"],
            "execution": {
                "execution_code": context["execution"]["execution_code"],
                "status": context["execution"]["status"],
                "progress": context["execution"]["progress"],
                "started_at": context["execution"]["started_at"],
                "finished_at": context["execution"]["finished_at"],
                "checklist_execution": context["execution"]["checklist_execution"],
                "diagnosis": context["execution"]["diagnosis"],
                "executed_action": context["execution"]["executed_action"],
                "materials": context["execution"]["materials"],
                "evidence": context["execution"]["evidence"],
                "finalization": context["execution"]["finalization"],
                "offline_sync": context["execution"].get("offline_sync", {}),
            },
            "sync": context["execution"].get("offline_sync", {}),
            "copilot": context["technician_copilot_bootstrap"],
        }
        context["page_title"] = f"Execucao {self.scoped_resource['service']['code']}"
        context["page_description"] = "Fluxo tecnico mobile-first para atendimento em campo."
        context["current_mobile_section"] = "services"
        return context


class TechnicianChecklistListView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/checklists_list.html"
    permission_domain = "checklists"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_technician_checklist_listing_context(self.request.user, self.get_tenant_context()))
        context["offline_bootstrap"] = {
            "screen": "checklists",
            "checklists": context["checklist_cards"],
        }
        context["page_title"] = "Checklists"
        context["page_description"] = "Rotinas tecnicas pendentes e em andamento."
        context["current_mobile_section"] = "checklists"
        return context


class TechnicianHistoryView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/history.html"
    permission_domain = "work_orders"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_technician_history_context(self.request.user, self.get_tenant_context()))
        context["offline_bootstrap"] = {
            "screen": "history",
            "history": context["history_records"],
        }
        context["page_title"] = "Historico"
        context["page_description"] = "Ultimos atendimentos concluidos e resultados recentes."
        context["current_mobile_section"] = "history"
        return context


class TechnicianProfileView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/profile.html"
    permission_domain = "work_execution"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_technician_profile_context(self.request.user, self.get_tenant_context()))
        context["offline_bootstrap"] = {
            "screen": "profile",
            "profile_cards": context["profile_cards"],
            "service_mix": context["service_mix"],
        }
        context["page_title"] = "Perfil"
        context["page_description"] = "Identidade de campo, cobertura e desempenho recente."
        context["current_mobile_section"] = "profile"
        return context


def _capture_service_signature_or_error(*, request, order_code, signature_kind):
    service_order = ServiceSignatureService.get_service_order(order_code)
    if service_order is None:
        return None, HttpResponseBadRequest("Ordem de servico nao encontrada para assinatura.")

    if signature_kind == "technician":
        form = TechnicianServiceSignatureForm(request.POST)
        signature_type = ServiceSignature.SignatureType.TECHNICIAN_COMPLETION
        signer_role = ServiceSignature.SignerRole.TECHNICIAN
    else:
        form = ClientServiceSignatureForm(request.POST)
        signature_type = ServiceSignature.SignatureType.CLIENT_ACCEPTANCE
        signer_role = ServiceSignature.SignerRole.CLIENT_RESPONSIBLE

    if not form.is_valid():
        return None, HttpResponseBadRequest(form.errors.as_json())

    signer_name = form.cleaned_data.get("signer_name") or (
        "Aceite nao coletado"
        if signature_kind == "client" and form.cleaned_data.get("missing_reason")
        else (request.user.display_name or request.user.full_name or "Responsavel nao identificado")
    )

    result = ServiceSignatureService.capture_signature(
        request=request,
        service_order=service_order,
        signature_type=signature_type,
        signer_role=signer_role,
        signer_name=signer_name,
        signer_title=form.cleaned_data.get("signer_title", ""),
        signer_document=form.cleaned_data.get("signer_document", ""),
        signer_user=request.user if signature_kind == "technician" else None,
        signature_data=form.cleaned_data.get("signature_data", ""),
        acceptance_notes=form.cleaned_data.get("acceptance_notes", ""),
        missing_reason=form.cleaned_data.get("missing_reason", ""),
        missing_reason_notes=form.cleaned_data.get("missing_reason_notes", ""),
        metadata={"origin": "technician_pwa" if request.path.startswith("/field/") else "admin_shell"},
    )
    return result, None


class TechnicianExecutionStartView(SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "mobile_work_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        AccessAuditService.log(
            user=request.user,
            action="mobile_execution_started",
            domain="execution",
            decision="allow",
            resource_type="service_order",
            resource_id=order_code,
            reason="technician mobile start",
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:technician-app-service-execution", order_code=order_code)


class TechnicianExecutionSaveView(SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "mobile_work_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        AccessAuditService.log(
            user=request.user,
            action="mobile_execution_saved",
            domain="execution",
            decision="allow",
            resource_type="service_order",
            resource_id=order_code,
            reason="technician mobile save progress",
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:technician-app-service-execution", order_code=order_code)


class TechnicianExecutionTechnicianSignatureView(SmartSystemAccessMixin, View):
    permission_domain = "service_signatures"
    permission_action = "capture"
    resource_type = "mobile_service_signature"
    log_permission_decision = True

    def post(self, request, order_code):
        result, error_response = _capture_service_signature_or_error(
            request=request,
            order_code=order_code,
            signature_kind="technician",
        )
        if error_response:
            return error_response
        AccessAuditService.log(
            user=request.user,
            action="mobile_technician_signature_saved",
            domain="service_signatures",
            decision="allow",
            resource_type="service_order",
            resource_id=order_code,
            reason="technician mobile signature saved",
            metadata={"signature_id": str(result.signature.public_id)},
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:technician-app-service-execution", order_code=order_code)


class TechnicianExecutionClientSignatureView(SmartSystemAccessMixin, View):
    permission_domain = "service_signatures"
    permission_action = "capture"
    resource_type = "mobile_service_signature"
    log_permission_decision = True

    def post(self, request, order_code):
        result, error_response = _capture_service_signature_or_error(
            request=request,
            order_code=order_code,
            signature_kind="client",
        )
        if error_response:
            return error_response
        AccessAuditService.log(
            user=request.user,
            action="mobile_client_signature_saved",
            domain="service_signatures",
            decision="allow",
            resource_type="service_order",
            resource_id=order_code,
            reason="client acceptance captured on technician mobile",
            metadata={"signature_id": str(result.signature.public_id)},
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:technician-app-service-execution", order_code=order_code)


class TechnicianExecutionCompleteView(SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "close"
    resource_type = "mobile_work_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        service_order = ServiceSignatureService.get_service_order(order_code)
        signature_summary = ServiceSignatureService.get_signature_summary(service_order)
        if not signature_summary["has_technician_signature"]:
            return redirect(f"{reverse('admin-shell:technician-app-service-execution', kwargs={'order_code': order_code})}?signature_error=technician")
        if not signature_summary["has_client_resolution"]:
            return redirect(f"{reverse('admin-shell:technician-app-service-execution', kwargs={'order_code': order_code})}?signature_error=client")
        AccessAuditService.log(
            user=request.user,
            action="mobile_execution_completed",
            domain="execution",
            decision="allow",
            resource_type="service_order",
            resource_id=order_code,
            reason="technician mobile completion",
            metadata={
                "has_technician_signature": signature_summary["has_technician_signature"],
                "has_client_signature": signature_summary["has_client_signature"],
                "missing_reason_recorded": signature_summary["missing_reason_recorded"],
            },
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:technician-app-service-detail", order_code=order_code)


class TechnicianSyncCenterView(TechnicianAppContextMixin, TemplateView):
    template_name = "technician_pwa/sync_center.html"
    permission_domain = "work_execution"
    permission_action = "execute"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["offline_bootstrap"] = {
            "screen": "sync_center",
            "bundle_url": "/field/api/offline-bundle/",
            "sync_url": "/field/api/offline-sync/",
        }
        context["page_title"] = "Sincronizacao"
        context["page_description"] = "Pendencias locais, reprocessamento e estado de conectividade do app de campo."
        context["current_mobile_section"] = "services"
        return context


class TechnicianOfflineBundleView(SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "view"
    resource_type = "technician_offline_bundle"
    log_permission_decision = True

    def get(self, request):
        bundle = get_technician_offline_bundle_context(request.user, build_shell_tenant_context(request))
        return JsonResponse(bundle)


class TechnicianCopilotContextView(SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "view"
    resource_type = "technician_copilot_context"
    log_permission_decision = True

    def get(self, request):
        order_code = request.GET.get("order_code", "")
        detail = get_technician_service_detail_context(request.user, build_shell_tenant_context(request), order_code)
        if detail is None:
            return JsonResponse({"detail": "Ordem de servico fora do escopo do tecnico."}, status=404)
        bootstrap = get_technician_copilot_bootstrap(detail)
        return JsonResponse(
            {
                "order_code": order_code,
                "context": bootstrap["context"],
                "suggestions": bootstrap["suggestions"],
                "maintenance_recommendations": bootstrap["maintenance_recommendations"],
                "recommended_parts": bootstrap["recommended_parts"],
            }
        )


class TechnicianCopilotSuggestionsView(SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "view"
    resource_type = "technician_copilot_suggestions"
    log_permission_decision = True

    def get(self, request):
        order_code = request.GET.get("order_code", "")
        detail = get_technician_service_detail_context(request.user, build_shell_tenant_context(request), order_code)
        if detail is None:
            return JsonResponse({"detail": "Ordem de servico fora do escopo do tecnico."}, status=404)
        bootstrap = get_technician_copilot_bootstrap(detail)
        return JsonResponse({"suggestions": bootstrap["suggestions"]})


class TechnicianCopilotQueryView(SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "view"
    resource_type = "technician_copilot_query"
    log_permission_decision = True

    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Payload JSON invalido."}, status=400)
        order_code = payload.get("order_code", "")
        query = payload.get("query", "").strip()
        if not order_code or not query:
            return JsonResponse({"detail": "order_code e query sao obrigatorios."}, status=400)
        tenant_context = build_shell_tenant_context(request)
        detail = get_technician_service_detail_context(request.user, tenant_context, order_code)
        if detail is None:
            return JsonResponse({"detail": "Ordem de servico fora do escopo do tecnico."}, status=404)
        bootstrap = get_technician_copilot_bootstrap(detail)
        service_order = ServiceSignatureService.get_service_order(order_code)
        response_payload = TechnicianCopilotService.handle_query(
            user=request.user,
            company=tenant_context.get("company"),
            site=tenant_context.get("site"),
            service_order=service_order,
            service_payload={
                **detail,
                "maintenance_recommendations": bootstrap["maintenance_recommendations"],
                "recommended_parts": bootstrap["recommended_parts"],
            },
            query=query,
            offline=bool(payload.get("offline")),
        )
        return JsonResponse(
            {
                "session_public_id": str(response_payload["session"].public_id),
                "context": response_payload["context"],
                "response": response_payload["response"],
            }
        )


class TechnicianCopilotSyncView(SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "technician_copilot_sync"
    log_permission_decision = True

    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Payload JSON invalido."}, status=400)
        order_code = payload.get("order_code", "")
        detail = get_technician_service_detail_context(request.user, build_shell_tenant_context(request), order_code)
        if detail is None:
            return JsonResponse({"detail": "Ordem de servico fora do escopo do tecnico."}, status=404)
        service_order = ServiceSignatureService.get_service_order(order_code)
        sync_result = TechnicianCopilotService.sync_local_session(
            user=request.user,
            company=self.get_current_company(),
            site=self.get_current_site(),
            service_order=service_order,
            payload=payload,
        )
        return JsonResponse({"messages_synced": sync_result["messages_synced"], "session_public_id": str(sync_result["session"].public_id)})


class TechnicianOfflineSyncView(SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "technician_offline_sync"
    log_permission_decision = True

    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Payload JSON invalido."}, status=400)
        operations = payload.get("operations") or []
        SystemEventService = None
        try:
            from apps.observability_center.services.observability_service import SystemEventService as _SystemEventService

            SystemEventService = _SystemEventService
        except Exception:
            SystemEventService = None
        if SystemEventService is not None:
            SystemEventService.log_system_event(
                event_type="sync.started",
                source_module="technician_pwa",
                message="Offline sync batch started.",
                entity_type="field_sync_batch",
                entity_id=str(len(operations)),
                user=request.user,
                company=self.get_current_company(),
                site=self.get_current_site(),
                payload={"operations": len(operations)},
            )
        response_payload = FieldOfflineSyncService.process_batch(request=request, user=request.user, operations=operations)
        return JsonResponse(response_payload)


@method_decorator(require_GET, name="dispatch")
class TechnicianServiceWorkerView(View):
    def get(self, request):
        javascript = """
const SHELL_CACHE = 'smart360-technician-shell-v3';
const RUNTIME_CACHE = 'smart360-technician-runtime-v3';
const PRECACHE_URLS = [
  '/field/',
  '/field/schedule/',
  '/field/services/',
  '/field/checklists/',
  '/field/history/',
  '/field/profile/',
  '/field/sync/',
  '/static/smart360/css/admin-shell.css',
  '/static/smart360/js/technician-copilot.js',
  '/static/smart360/js/technician-offline.js',
  '/static/smart360/pwa/technician.webmanifest',
  '/static/smart360/pwa/icon-technician-192.svg',
  '/static/smart360/pwa/icon-technician-512.svg'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(function(cache) {
      return cache.addAll(PRECACHE_URLS);
    }).catch(function() {
      return Promise.resolve();
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.map(function(key) {
        if (key !== SHELL_CACHE && key !== RUNTIME_CACHE) {
          return caches.delete(key);
        }
        return Promise.resolve();
      }));
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  const request = event.request;
  if (request.method !== 'GET') {
    return;
  }
  const url = new URL(request.url);
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(function(response) {
        const clone = response.clone();
        caches.open(RUNTIME_CACHE).then(function(cache) { cache.put(request, clone); });
        return response;
      }).catch(function() {
        return caches.match(request).then(function(cached) {
          return cached || caches.match('/field/');
        });
      })
    );
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(function(cached) {
        if (cached) {
          return cached;
        }
        return fetch(request).then(function(response) {
          const clone = response.clone();
          caches.open(RUNTIME_CACHE).then(function(cache) { cache.put(request, clone); });
          return response;
        });
      })
    );
    return;
  }
  if (url.pathname.startsWith('/field/')) {
    event.respondWith(
      fetch(request).then(function(response) {
        const clone = response.clone();
        caches.open(RUNTIME_CACHE).then(function(cache) { cache.put(request, clone); });
        return response;
      }).catch(function() {
        return caches.match(request);
      })
    );
  }
});
"""
        return HttpResponse(javascript, content_type="application/javascript")


class ClientPortalDashboardView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/dashboard.html"
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_dashboard_context(self.request, self.get_tenant_context()))
        context["page_title"] = "Dashboard"
        context["page_description"] = "Visao executiva da operacao do seu contrato com o Smart System."
        context["breadcrumbs"] = [{"label": "Portal do Cliente", "url": None}]
        context["current_portal_section"] = "dashboard"
        context["latest_briefing"] = AIBriefingComposer.latest_for_context(
            company=self.get_tenant_context().get("company"),
            audience=AIBriefing.Audience.CLIENT,
            user=self.request.user,
            site=self.get_tenant_context().get("site"),
        )
        return context


class ClientPortalAssetListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/assets_list.html"
    permission_domain = "client_portal_assets"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_client_asset_listing_context(self.request, filters, self.get_tenant_context()))
        context["page_title"] = "Ativos"
        context["page_description"] = "Consulta de ativos monitorados, status operacional e manutencao recente."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Ativos", "url": None},
        ]
        context["current_portal_section"] = "assets"
        return context


class ClientPortalAssetDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/asset_detail.html"
    permission_domain = "client_portal_assets"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_asset_detail_context(self.request, self.kwargs["asset_code"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["asset"].name
        context["page_description"] = payload["asset"].asset_tag
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Ativos", "url": "admin-shell:client-portal-assets"},
            {"label": payload["asset"].asset_tag, "url": None},
        ]
        context["current_portal_section"] = "assets"
        return context


class ClientPortalWorkOrderListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/work_orders_list.html"
    permission_domain = "client_portal_work_orders"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_client_work_order_listing_context(self.request, filters))
        context["page_title"] = "Ordens de Servico"
        context["page_description"] = "Acompanhamento de status, prioridade e atendimento das ordens do seu ambiente."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Ordens de Servico", "url": None},
        ]
        context["current_portal_section"] = "work-orders"
        return context


class ClientPortalWorkOrderDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/work_order_detail.html"
    permission_domain = "client_portal_work_orders"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_work_order_detail_context(self.request, self.kwargs["order_code"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["work_order"].order_number
        context["page_description"] = payload["work_order"].title
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Ordens de Servico", "url": "admin-shell:client-portal-work-orders"},
            {"label": payload["work_order"].order_number, "url": None},
        ]
        context["current_portal_section"] = "work-orders"
        return context


class ClientPortalPreventiveListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/preventives_list.html"
    permission_domain = "client_portal_preventives"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_client_preventive_listing_context(self.request, filters))
        context["page_title"] = "Preventivas"
        context["page_description"] = "Cobertura preventiva, proximas janelas e execucoes recentes."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Preventivas", "url": None},
        ]
        context["current_portal_section"] = "preventives"
        return context


class ClientPortalPreventiveDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/preventive_detail.html"
    permission_domain = "client_portal_preventives"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_preventive_detail_context(self.request, self.kwargs["public_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["plan"].name
        context["page_description"] = payload["plan"].asset.asset_tag if payload["plan"].asset else "Preventiva"
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Preventivas", "url": "admin-shell:client-portal-preventives"},
            {"label": payload["plan"].name, "url": None},
        ]
        context["current_portal_section"] = "preventives"
        return context


class ClientPortalReportListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/reports_list.html"
    permission_domain = "client_portal_reports"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_report_listing_context(self.get_tenant_context()))
        context["page_title"] = "Relatorios"
        context["page_description"] = "Documentos tecnicos, fichas resumidas e evidencias liberadas para o cliente."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Relatorios", "url": None},
        ]
        context["current_portal_section"] = "reports"
        return context


class ClientPortalReportPreviewView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/report_preview.html"
    permission_domain = "client_portal_reports"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_report_preview(self.kwargs["report_type"], self.kwargs["reference_code"], self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["report"]["report_code"]
        context["page_description"] = payload["report"]["document_type"]
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Relatorios", "url": "admin-shell:client-portal-reports"},
            {"label": payload["report"]["report_code"], "url": None},
        ]
        context["current_portal_section"] = "reports"
        context["page_actions"] = [
            {"label": "Baixar PDF", "href": f"/app/client-portal/reports/{self.kwargs['report_type']}/{self.kwargs['reference_code']}/download/", "permission_domain": "client_portal_reports", "permission_action": "export"},
            {"label": "Voltar para relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
        ]
        return context


class ClientPortalReportDownloadView(ClientPortalAccessMixin, View):
    permission_domain = "client_portal_reports"
    permission_action = "export"
    resource_type = "client_portal_report"
    log_permission_decision = True

    def get(self, request, report_type, reference_code):
        try:
            payload = generate_client_report_pdf(report_type, reference_code, self.get_current_tenant_context())
        except RuntimeError as exc:
            return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")
        if payload is None:
            return self.handle_scope_denied()
        AccessAuditService.log(
            user=request.user,
            action="client_portal_report_exported",
            domain="client_portal_reports",
            decision="allow",
            resource_type=report_type,
            resource_id=reference_code,
            metadata={"filename": payload["filename"]},
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        response = HttpResponse(payload["bytes"], content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{payload["filename"]}"'
        return response

    def get_current_tenant_context(self):
        return build_shell_tenant_context(self.request)


class ClientPortalQuoteListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/quotes_list.html"
    permission_domain = "client_portal_quotes"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_quote_listing_context(self.request))
        context["page_title"] = "Orcamentos"
        context["page_description"] = "Acompanhe pecas, mao de obra e decisoes pendentes de aprovacao."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Orcamentos", "url": None},
        ]
        context["current_portal_section"] = "quotes"
        return context


class ClientPortalQuoteDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/quote_detail.html"
    permission_domain = "client_portal_quotes"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_quote_detail_context(self.request, self.kwargs["quote_number"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["quote_decision_form"] = ClientQuoteDecisionForm()
        context["page_title"] = self.scoped_resource["quote"].quote_number
        context["page_description"] = f"Orcamento vinculado a {self.scoped_resource['quote'].work_order.order_number}"
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Orcamentos", "url": "admin-shell:client-portal-quotes"},
            {"label": self.scoped_resource["quote"].quote_number, "url": None},
        ]
        context["current_portal_section"] = "quotes"
        return context


class ClientPortalQuoteApproveView(ClientPortalAccessMixin, View):
    permission_domain = "client_portal_quotes"
    permission_action = "approve"
    resource_type = "client_portal_quote"
    log_permission_decision = True

    def post(self, request, quote_number):
        payload = get_client_quote_detail_context(request, quote_number)
        if payload is None:
            return self.handle_scope_denied()
        form = ClientQuoteDecisionForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(form.errors.as_json())
        quote = ServiceQuoteService.approve_quote(
            quote=payload["quote"],
            approver_name=form.cleaned_data.get("signer_name") or request.user.display_name or request.user.email,
            approver_user=request.user,
            notes=form.cleaned_data.get("notes", ""),
        )
        return redirect("admin-shell:client-portal-quote-detail", quote_number=quote.quote_number)


class ClientPortalQuoteRejectView(ClientPortalAccessMixin, View):
    permission_domain = "client_portal_quotes"
    permission_action = "reject"
    resource_type = "client_portal_quote"
    log_permission_decision = True

    def post(self, request, quote_number):
        payload = get_client_quote_detail_context(request, quote_number)
        if payload is None:
            return self.handle_scope_denied()
        form = ClientQuoteDecisionForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(form.errors.as_json())
        quote = ServiceQuoteService.reject_quote(
            quote=payload["quote"],
            approver_name=form.cleaned_data.get("signer_name") or request.user.display_name or request.user.email,
            approver_user=request.user,
            reason=form.cleaned_data.get("rejection_reason", "") or form.cleaned_data.get("notes", ""),
        )
        return redirect("admin-shell:client-portal-quote-detail", quote_number=quote.quote_number)


class ClientPortalContractListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/contracts_list.html"
    permission_domain = "client_portal_contracts"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_contract_listing_context(self.request))
        context["page_title"] = "Contratos de Manutencao"
        context["page_description"] = "Cobertura contratual, ativos inclusos e recorrencia preventiva do seu ambiente."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Contratos", "url": None},
        ]
        context["current_portal_section"] = "contracts"
        return context


class ClientPortalContractDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/contract_detail.html"
    permission_domain = "client_portal_contracts"
    permission_action = "view"
    resource_type = "client_portal_contract"

    def load_scoped_resource(self):
        return get_client_contract_detail_context(self.request, self.kwargs["contract_number"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["page_title"] = self.scoped_resource["contract"].contract_number
        context["page_description"] = f"Contrato recorrente de {self.scoped_resource['contract'].client.display_name}"
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Contratos", "url": "admin-shell:client-portal-contracts"},
            {"label": self.scoped_resource["contract"].contract_number, "url": None},
        ]
        context["current_portal_section"] = "contracts"
        return context


class ClientPortalRequestListView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/requests_list.html"
    permission_domain = "client_portal_requests"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_client_request_listing_context(self.request, filters, self.get_tenant_context()))
        context["page_title"] = "Solicitacoes"
        context["page_description"] = "Abertura e acompanhamento de chamados, necessidades e solicitacoes do cliente."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Solicitacoes", "url": None},
        ]
        context["current_portal_section"] = "requests"
        return context


class ClientPortalRequestCreateView(ClientPortalContextMixin, FormView):
    template_name = "client_portal/request_create.html"
    form_class = ClientPortalRequestForm
    permission_domain = "client_portal_requests"
    permission_action = "create"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def form_valid(self, form):
        portal_request = create_client_portal_request(
            form,
            user=self.request.user,
            tenant_context=self.get_tenant_context(),
        )
        AccessAuditService.log(
            user=self.request.user,
            action="client_portal_request_created",
            domain="client_portal_requests",
            decision="allow",
            resource_type="client_portal_request",
            resource_id=portal_request.protocol_number,
            metadata={"category": portal_request.category, "priority": portal_request.priority},
            company=portal_request.company,
            site=portal_request.operational_site,
        )
        return redirect("admin-shell:client-portal-request-detail", protocol_number=portal_request.protocol_number)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Abrir solicitacao"
        context["page_description"] = "Registre uma necessidade operacional, visita ou problema para acompanhamento pela equipe SMART360."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Solicitacoes", "url": "admin-shell:client-portal-requests"},
            {"label": "Nova solicitacao", "url": None},
        ]
        context["current_portal_section"] = "requests"
        context["page_actions"] = [
            {"label": "Voltar para solicitacoes", "route_name": "admin-shell:client-portal-requests", "permission_domain": "client_portal_requests", "permission_action": "view"},
        ]
        return context


class ClientPortalRequestDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/request_detail.html"
    permission_domain = "client_portal_requests"
    permission_action = "view"

    def load_scoped_resource(self):
        return get_client_request_detail_context(self.request, self.kwargs["protocol_number"], self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["client_request"].protocol_number
        context["page_description"] = payload["client_request"].title
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Solicitacoes", "url": "admin-shell:client-portal-requests"},
            {"label": payload["client_request"].protocol_number, "url": None},
        ]
        context["current_portal_section"] = "requests"
        return context


class ClientPortalSitesView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/sites_list.html"
    permission_domain = "client_portal_sites"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_site_listing_context(self.request))
        context["page_title"] = "Unidades"
        context["page_description"] = "Visao consolidada das unidades monitoradas no seu contrato."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Unidades", "url": None},
        ]
        context["current_portal_section"] = "sites"
        return context


class ClientPortalProfileView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/profile.html"
    permission_domain = "client_portal_profile"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_client_profile_context(self.request.user, self.get_tenant_context()))
        context["page_title"] = "Meu perfil"
        context["page_description"] = "Dados do usuario, escopo autorizado e contexto do portal."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Meu perfil", "url": None},
        ]
        context["current_portal_section"] = "profile"
        return context


class ClientPortalBriefingDetailView(ClientPortalScopedResourceTemplateView):
    template_name = "client_portal/briefing_detail.html"
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def load_scoped_resource(self):
        return AIBriefingComposer.list_accessible_briefings(
            user=self.request.user,
            company=self.get_tenant_context().get("company"),
            audience=AIBriefing.Audience.CLIENT,
        ).filter(public_id=self.kwargs["briefing_id"]).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        briefing = self.scoped_resource
        AIBriefingComposer.mark_viewed(briefing=briefing, user=self.request.user)
        context["briefing"] = briefing
        context["page_title"] = briefing.title
        context["page_description"] = briefing.summary
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "Briefing", "url": None},
        ]
        context["current_portal_section"] = "dashboard"
        return context


class ClientPortalCopilotView(ClientPortalContextMixin, TemplateView):
    template_name = "client_portal/copilot.html"
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        seed_context = {
            "asset": self.request.GET.get("asset", ""),
            "work_order": self.request.GET.get("work_order", ""),
            "quote": self.request.GET.get("quote", ""),
            "contract": self.request.GET.get("contract", ""),
            "preventive": self.request.GET.get("preventive", ""),
            "request": self.request.GET.get("request", ""),
            "report_type": self.request.GET.get("report_type", ""),
            "reference_code": self.request.GET.get("reference_code", ""),
        }
        payload = ClientPortalCopilotService.get_current_context_payload(
            request=self.request,
            tenant_context=self.get_tenant_context(),
            permission_map=self.get_permission_map(),
            session_public_id=self.request.GET.get("session"),
            context_seed=seed_context,
        )
        context["copilot_session"] = payload["session"]
        context["copilot_context"] = payload["context"]
        context["copilot_suggestions"] = payload["suggestions"]
        context["copilot_messages"] = list(payload["session"].messages.order_by("created_at")[:20])
        context["copilot_pending_cards"] = ClientPortalCopilotService.list_pending_cards(
            request=self.request,
            tenant_context=self.get_tenant_context(),
            permission_map=self.get_permission_map(),
        )
        context["copilot_seed_context"] = {
            **seed_context,
            "question": self.request.GET.get("question", ""),
        }
        context["page_title"] = "AI Copilot para Cliente"
        context["page_description"] = "Contexto operacional, explicacoes claras e proximos passos dentro do seu portal SMART360."
        context["breadcrumbs"] = [
            {"label": "Portal do Cliente", "url": "admin-shell:client-portal-dashboard"},
            {"label": "AI Copilot", "url": None},
        ]
        context["current_portal_section"] = "dashboard"
        return context


class ClientPortalCopilotQueryView(ClientPortalShellAccessMixin, View):
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return HttpResponseBadRequest("payload_invalido")
        result = ClientPortalCopilotService.handle_query(
            request=request,
            tenant_context=build_shell_tenant_context(request),
            permission_map=self.get_permission_map(),
            query=payload.get("query", ""),
            session_public_id=payload.get("session_public_id"),
            context_seed=payload.get("context_seed") or {},
        )
        return JsonResponse(
            {
                "session": {
                    "public_id": str(result["session"].public_id),
                    "message_count": result["session"].message_count,
                    "last_intent": result["session"].last_intent,
                },
                "context": result["context"],
                "response": result["response"],
                "suggestions": result["suggestions"],
            }
        )


class ClientPortalCopilotContextView(ClientPortalShellAccessMixin, View):
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        payload = ClientPortalCopilotService.get_current_context_payload(
            request=request,
            tenant_context=build_shell_tenant_context(request),
            permission_map=self.get_permission_map(),
            session_public_id=request.GET.get("session"),
            context_seed={
                "asset": request.GET.get("asset", ""),
                "work_order": request.GET.get("work_order", ""),
                "quote": request.GET.get("quote", ""),
                "contract": request.GET.get("contract", ""),
                "preventive": request.GET.get("preventive", ""),
                "request": request.GET.get("request", ""),
                "report_type": request.GET.get("report_type", ""),
                "reference_code": request.GET.get("reference_code", ""),
            },
        )
        return JsonResponse(
            {
                "session": {
                    "public_id": str(payload["session"].public_id),
                    "message_count": payload["session"].message_count,
                    "last_intent": payload["session"].last_intent,
                },
                "context": payload["context"],
                "suggestions": payload["suggestions"],
            }
        )


class ClientPortalCopilotSuggestionsView(ClientPortalShellAccessMixin, View):
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        payload = ClientPortalCopilotService.get_current_context_payload(
            request=request,
            tenant_context=build_shell_tenant_context(request),
            permission_map=self.get_permission_map(),
            session_public_id=request.GET.get("session"),
        )
        return JsonResponse({"suggestions": payload["suggestions"]})


class ClientPortalCopilotPendingItemsView(ClientPortalShellAccessMixin, View):
    permission_domain = "client_portal_dashboard"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        payload = ClientPortalCopilotService.list_pending_cards(
            request=request,
            tenant_context=build_shell_tenant_context(request),
            permission_map=self.get_permission_map(),
        )
        return JsonResponse(payload)


class MarketplaceTechniciansDashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_dashboard.html"
    permission_domain = "marketplace_dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_marketplace_dashboard_context(self.request.user))
        context["page_title"] = "Marketplace de Tecnicos"
        context["page_description"] = "Rede operacional de tecnicos, ofertas, atribuicoes e execucao de servicos em campo."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Dashboard", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = context["page_actions"]
        return context


class MarketplaceTechniciansRequestListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_requests.html"
    permission_domain = "marketplace_requests"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_service_request_listing_context(self.request.user, filters))
        context["page_title"] = "Service Requests"
        context["page_description"] = "Demandas publicadas pelas empresas, com prioridade, ofertas recebidas e prontidao para atribuicao."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Service Requests", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Dashboard", "route_name": "admin-shell:marketplace-technicians-dashboard", "permission_domain": "marketplace_dashboard", "permission_action": "view"},
            {"label": "Offers", "route_name": "admin-shell:marketplace-technicians-offers", "permission_domain": "marketplace_offers", "permission_action": "view"},
            {"label": "Technicians", "route_name": "admin-shell:marketplace-technicians-technicians", "permission_domain": "marketplace_technicians", "permission_action": "view"},
        ]
        return context


class MarketplaceTechniciansOfferListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_offers.html"
    permission_domain = "marketplace_offers"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_service_offer_listing_context(self.request.user, filters))
        context["page_title"] = "Service Offers"
        context["page_description"] = "Ofertas recebidas, aceite comercial e disputa operacional por atendimento."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Offers", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Requests", "route_name": "admin-shell:marketplace-technicians-requests", "permission_domain": "marketplace_requests", "permission_action": "view"},
            {"label": "Assignments", "route_name": "admin-shell:marketplace-technicians-assignments", "permission_domain": "marketplace_assignments", "permission_action": "view"},
        ]
        return context


class MarketplaceTechniciansMatchingListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_matching.html"
    permission_domain = "marketplace_matching"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_matching_listing_context(self.request.user, filters))
        context["page_title"] = "Matching Inteligente"
        context["page_description"] = "Ranking tecnico calculado por especialidade, distancia, disponibilidade, reputacao e experiencia."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Matching", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Dashboard", "route_name": "admin-shell:marketplace-technicians-dashboard", "permission_domain": "marketplace_dashboard", "permission_action": "view"},
            {"label": "Requests", "route_name": "admin-shell:marketplace-technicians-requests", "permission_domain": "marketplace_requests", "permission_action": "view"},
            {"label": "Offers", "route_name": "admin-shell:marketplace-technicians-offers", "permission_domain": "marketplace_offers", "permission_action": "view"},
        ]
        return context


class MarketplaceTechniciansTechnicianListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_list.html"
    permission_domain = "marketplace_technicians"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_technician_listing_context(self.request.user, filters))
        context["page_title"] = "Technicians"
        context["page_description"] = "Perfis tecnicos, especialidades, cobertura regional e reputacao operacional."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Technicians", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Dashboard", "route_name": "admin-shell:marketplace-technicians-dashboard", "permission_domain": "marketplace_dashboard", "permission_action": "view"},
            {"label": "Requests", "route_name": "admin-shell:marketplace-technicians-requests", "permission_domain": "marketplace_requests", "permission_action": "view"},
        ]
        return context


class MarketplaceTechnicianDetailView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technician_detail.html"
    permission_domain = "marketplace_technicians"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = get_technician_detail_context(self.request.user, self.kwargs["public_id"])
        if payload is None:
            raise Http404("Tecnico nao encontrado.")
        context.update(payload)
        context["page_title"] = payload["technician"].display_name
        context["page_description"] = "Perfil profissional, regioes, especialidades, historico e reputacao."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Technicians", "url": "admin-shell:marketplace-technicians-technicians"},
            {"label": payload["technician"].display_name, "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Technicians", "route_name": "admin-shell:marketplace-technicians-technicians", "permission_domain": "marketplace_technicians", "permission_action": "view"},
            {"label": "Assignments", "route_name": "admin-shell:marketplace-technicians-assignments", "permission_domain": "marketplace_assignments", "permission_action": "view"},
        ]
        return context


class MarketplaceTechniciansAssignmentListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_assignments.html"
    permission_domain = "marketplace_assignments"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_assignment_listing_context(self.request.user, filters))
        context["page_title"] = "Assignments"
        context["page_description"] = "Atribuicoes ativas do marketplace e vinculacao operacional com a execucao de campo."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Assignments", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Requests", "route_name": "admin-shell:marketplace-technicians-requests", "permission_domain": "marketplace_requests", "permission_action": "view"},
            {"label": "Reviews", "route_name": "admin-shell:marketplace-technicians-reviews", "permission_domain": "marketplace_reviews", "permission_action": "view"},
        ]
        return context


class MarketplaceTechniciansReviewListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/marketplace_technicians_reviews.html"
    permission_domain = "marketplace_reviews"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_review_listing_context(self.request.user, filters))
        context["page_title"] = "Reviews"
        context["page_description"] = "Avaliacao pos-servico, reputacao e qualidade percebida pelos clientes."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Marketplace", "url": None},
            {"label": "Reviews", "url": None},
        ]
        context["current_module_slug"] = "marketplace-technicians"
        context["page_actions"] = [
            {"label": "Assignments", "route_name": "admin-shell:marketplace-technicians-assignments", "permission_domain": "marketplace_assignments", "permission_action": "view"},
            {"label": "Technicians", "route_name": "admin-shell:marketplace-technicians-technicians", "permission_domain": "marketplace_technicians", "permission_action": "view"},
        ]
        return context


class AnalyticsExecutiveDashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/analytics_executive_dashboard.html"
    permission_domain = "analytics_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(
            get_analytics_executive_context(
                user=self.request.user,
                tenant_context=self.get_tenant_context(),
                filters=filters,
            )
        )
        context["page_title"] = "Analytics Executivo"
        context["page_description"] = "Rentabilidade operacional, SLA, produtividade tecnica e leitura financeira executiva."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Intelligence", "url": None},
            {"label": "Analytics Executivo", "url": None},
        ]
        context["current_module_slug"] = "analytics-platform"
        context["page_actions"] = [
            {"label": "Atualizar snapshot", "route_name": "admin-shell:analytics-executive-refresh", "permission_domain": "analytics_admin", "permission_action": "manage"},
            {"label": "Revenue API", "href": "/api/v1/analytics/revenue/", "permission_domain": "analytics_admin", "permission_action": "view"},
            {"label": "Profitability API", "href": "/api/v1/analytics/profitability/", "permission_domain": "analytics_admin", "permission_action": "view"},
            {"label": "Abrir Copilot", "href": f"{reverse('admin-shell:ai-manager-copilot')}?source=analytics", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context


class ExecutiveWarRoomView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/executive_war_room.html"
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(
            build_executive_war_room_context(
                user=self.request.user,
                tenant_context=self.get_tenant_context(),
                filters=filters,
            )
        )
        context["page_title"] = "Executive War Room"
        context["page_description"] = "Centro de comando executivo do SMART360 com operacao, IA, risco, agenda, marketplace e rentabilidade em uma unica visao."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Executive War Room", "url": None},
        ]
        context["current_module_slug"] = "analytics-platform"
        context["page_actions"] = [
            {"label": "Atualizar War Room", "href": reverse("admin-shell:executive-war-room"), "permission_domain": "dashboard", "permission_action": "view"},
            {"label": "Abrir Copilot", "href": f"{reverse('admin-shell:ai-manager-copilot')}?question=Resuma o war room atual", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Decisoes pendentes", "route_name": "admin-shell:ai-decision-center", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Analytics Executivo", "route_name": "admin-shell:analytics-executive-dashboard", "permission_domain": "analytics_admin", "permission_action": "view"},
        ]
        return context


class ExecutiveWarRoomDataView(ShellContextMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = False

    def get(self, request, *args, **kwargs):
        filters = {key: value for key, value in request.GET.items() if value}
        payload = build_executive_war_room_context(
            user=request.user,
            tenant_context=self.get_tenant_context(),
            filters=filters,
        )
        return JsonResponse(payload["war_room_api_payload"])


class ExecutiveWarRoomRealtimeStreamView(ShellContextMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = False

    def get(self, request, *args, **kwargs):
        tenant_context = self.get_tenant_context()
        company = tenant_context.get("active_company") or tenant_context.get("company")
        site = tenant_context.get("active_site") or tenant_context.get("site")
        return RealtimeEventBus.sse_snapshot_response(
            company=company,
            site=site,
            last_event_id=request.GET.get("lastEventId", ""),
        )


class AnalyticsExecutiveRefreshView(ShellContextMixin, View):
    permission_domain = "analytics_admin"
    permission_action = "manage"
    enforce_billing_access = False

    def get(self, request, *args, **kwargs):
        tenant_context = self.get_tenant_context()
        active_company = tenant_context.get("active_company")
        if active_company is not None:
            ExecutiveAnalyticsService.refresh_company_snapshots(
                company=active_company,
                period_type=request.GET.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
                user=request.user,
            )
        return redirect(reverse("admin-shell:analytics-executive-dashboard"))


class OperationsHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/operations_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_operations_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Operação Técnica Inteligente"
        context["page_description"] = "Resumo prático dos agentes de manutenção e agenda para gestão operacional."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Operações", "url": None},
            {"label": "Operação Técnica Inteligente", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        context["page_actions"] = [
            {"label": "Recomendações", "route_name": "admin-shell:ai-agents-recommendations", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Propostas", "route_name": "admin-shell:ai-agents-proposals", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Runs", "route_name": "admin-shell:ai-agents-runs", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context


class AIAgentsDashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_dashboard.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_dashboard_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "AI Agents Center"
        context["page_description"] = "Centro de comando de agentes autonomos com recommendations, action proposals e runs auditaveis."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Intelligence", "url": None},
            {"label": "AI Agents Center", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        context["page_actions"] = [
            {"label": "AI Briefings", "route_name": "admin-shell:ai-briefings", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Manager Copilot", "route_name": "admin-shell:ai-manager-copilot", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Recommendations", "route_name": "admin-shell:ai-agents-recommendations", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Maintenance Health", "route_name": "admin-shell:ai-agents-maintenance-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Schedule Health", "route_name": "admin-shell:ai-agents-scheduling-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Economic Health", "route_name": "admin-shell:ai-agents-profitability-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Marketplace Health", "route_name": "admin-shell:ai-agents-marketplace-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Anomaly Health", "route_name": "admin-shell:ai-agents-anomaly-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Runs", "route_name": "admin-shell:ai-agents-runs", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Action Proposals", "route_name": "admin-shell:ai-agents-proposals", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context


class AIManagerCopilotView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_manager_copilot.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        seed_context = {
            "asset": self.request.GET.get("asset", ""),
            "client": self.request.GET.get("client", ""),
            "contract": self.request.GET.get("contract", ""),
            "technician": self.request.GET.get("technician", ""),
            "site": self.request.GET.get("site", ""),
            "question": self.request.GET.get("question", ""),
            "source": self.request.GET.get("source", ""),
        }
        context.update(
            get_ai_manager_copilot_context(
                tenant_context=self.get_tenant_context(),
                user=self.request.user,
                seed_context=seed_context,
                session_public_id=self.request.GET.get("session"),
            )
        )
        context["page_title"] = "AI Copilot para Gestor"
        context["page_description"] = "Leitura executiva contextual, recomendacoes dos agentes e apoio guiado a decisao com escopo seguro."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Intelligence", "url": None},
            {"label": "AI Copilot para Gestor", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        context["page_actions"] = [
            {"label": "Briefings", "route_name": "admin-shell:ai-briefings", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Recommendations", "route_name": "admin-shell:ai-agents-recommendations", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Action Proposals", "route_name": "admin-shell:ai-agents-proposals", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Anomaly Health", "route_name": "admin-shell:ai-agents-anomaly-health", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context


class AIBriefingListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_briefings_list.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_ai_briefings_context(tenant_context=self.get_tenant_context(), user=self.request.user, filters=filters))
        context["page_title"] = "AI Briefings"
        context["page_description"] = "Briefings automaticos diarios, semanais e sob demanda para gestores, tecnicos e clientes."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "AI Briefings", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        context["page_actions"] = [
            {"label": "Gerar sob demanda", "route_name": "admin-shell:ai-briefing-generate", "permission_domain": "ai_agents_admin", "permission_action": "manage"},
        ]
        return context


class AIBriefingDetailView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_briefing_detail.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = AIBriefingComposer.list_accessible_briefings(
            user=self.request.user,
            company=self.get_tenant_context().get("active_company") or self.get_tenant_context().get("company"),
        )
        briefing = get_object_or_404(queryset, public_id=self.kwargs["briefing_id"])
        AIBriefingComposer.mark_viewed(briefing=briefing, user=self.request.user)
        context["briefing"] = briefing
        context["page_title"] = briefing.title
        context["page_description"] = briefing.summary
        context["breadcrumbs"] = [
            {"label": "AI Briefings", "url": "admin-shell:ai-briefings"},
            {"label": briefing.title, "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIBriefingGenerateView(ShellContextMixin, View):
    permission_domain = "ai_agents_admin"
    permission_action = "manage"
    enforce_billing_access = False

    def post(self, request, *args, **kwargs):
        tenant_context = self.get_tenant_context()
        company = tenant_context.get("active_company") or tenant_context.get("company")
        site = tenant_context.get("active_site") or tenant_context.get("site")
        briefing_type = request.POST.get("briefing_type", AIBriefing.BriefingType.ON_DEMAND)
        audience = request.POST.get("audience", AIBriefing.Audience.MANAGER)
        target_user = request.user
        if request.POST.get("user_id"):
            from apps.users.models import User

            target_user = User.objects.filter(pk=request.POST["user_id"]).first() or request.user
        briefing = AIBriefingComposer.generate_briefing(
            briefing_type=briefing_type,
            audience=audience,
            company=company,
            user=target_user if audience != AIBriefing.Audience.MANAGER or briefing_type == AIBriefing.BriefingType.ON_DEMAND else request.user,
            site=site,
            start=timezone.datetime.strptime(request.POST["start"], "%Y-%m-%d").date() if request.POST.get("start") else None,
            end=timezone.datetime.strptime(request.POST["end"], "%Y-%m-%d").date() if request.POST.get("end") else None,
            filters={"source": "shell"},
        )
        AIBriefingComposer.deliver_briefing(briefing=briefing)
        return redirect("admin-shell:ai-briefing-detail", briefing_id=briefing.public_id)


class AIAgentRecommendationsView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_recommendations.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_recommendations_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Agent Recommendations"
        context["page_description"] = "Recomendacoes estruturadas geradas pelos agentes com contexto, severidade e entidade alvo."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Recommendations", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        context["page_actions"] = [
            {"label": "Manager Copilot", "route_name": "admin-shell:ai-manager-copilot", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Action Proposals", "route_name": "admin-shell:ai-agents-proposals", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context


class AIAgentRunsView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_runs.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_runs_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Agent Runs"
        context["page_description"] = "Historico de execucoes dos agentes com trigger, tenant, duracao e status."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Runs", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentMaintenanceHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_maintenance_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_maintenance_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Maintenance Health"
        context["page_description"] = "Ativos em observacao pelo Maintenance Intelligence Agent com risco, sinais e recomendacao atual."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Maintenance Health", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentSchedulingHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_scheduling_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_scheduling_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Schedule Health"
        context["page_description"] = "Saude operacional da agenda com sobrecarga, conflitos, risco de SLA e oportunidades de redistribuicao."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Schedule Health", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentProfitabilityHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_profitability_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_profitability_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Economic Health"
        context["page_description"] = "Saude economica com clientes, contratos, rotas e atendimentos sob atencao do Profitability Agent."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Economic Health", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentMarketplaceHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_marketplace_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_marketplace_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Marketplace Health"
        context["page_description"] = "Requests do marketplace sob atencao com melhor candidato viavel, risco de SLA e fallback operacional."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Marketplace Health", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentAnomalyHealthView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_agents_anomaly_health.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_agents_anomaly_health_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Anomaly Health"
        context["page_description"] = "Radar do ecossistema com desvios em falhas, backlog, SLA, pecas, marketplace e margem."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Anomaly Health", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAgentActionProposalsView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_decision_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_decision_center_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "AI Decision Engine"
        context["page_description"] = "Centro de comando para decidir, aprovar, executar e auditar acoes assistidas por IA."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "AI Decision Engine", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AISimulationCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_simulation_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_simulation_center_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Simulation Engine"
        context["page_description"] = "Comparacao de cenarios operacionais, financeiros e de agenda antes da acao."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Simulation Engine", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIOptimizationCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_optimization_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_optimization_center_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Auto-Optimization Loop"
        context["page_description"] = "Qualidade operacional da IA, outcomes observados, feedbacks e ajustes supervisionados."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Auto-Optimization Loop", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIPolicyStudioView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_policy_studio.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_policy_studio_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Policy Studio"
        context["page_description"] = "Governanca central da IA por tenant, modulo, acao, risco e autonomia."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Policy Studio", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIExperimentationCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_experimentation_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_experimentation_center_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Experimentation Framework"
        context["page_description"] = "A/B testing auditavel de heuristicas, agentes, politicas e estrategias de IA."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Experimentation Framework", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIAutonomyCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_autonomy_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_autonomy_center_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Autonomous Operations Mode"
        context["page_description"] = "Cockpit de autonomia supervisionada com safety envelope, guards, kill switch e incidentes."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Autonomous Operations Mode", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIDigitalTwinCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_digital_twin_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            get_ai_digital_twin_context(
                tenant_context=self.get_tenant_context(),
                twin_public_id=self.request.GET.get("twin"),
            )
        )
        context["page_title"] = "Digital Twin Operacional"
        context["page_description"] = "Representacao viva de unidades e ativos com estado, risco, sinais, timeline e contexto para IA."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Digital Twin Operacional", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIKnowledgeGraphCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_knowledge_graph_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            get_ai_knowledge_graph_context(
                tenant_context=self.get_tenant_context(),
                node_public_id=self.request.GET.get("node"),
            )
        )
        context["page_title"] = "Knowledge Graph Industrial"
        context["page_description"] = "Memoria relacional do ecossistema ligando ativos, falhas, pecas, tecnicos, contratos, recomendacoes e decisoes."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "Knowledge Graph", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIVoiceOpsCenterView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/ai_voiceops_center.html"
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_ai_voiceops_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "VoiceOps"
        context["page_description"] = "Interface por voz para tecnico, gestor e cliente com intents operacionais, auditoria e resposta contextual."
        context["breadcrumbs"] = [
            {"label": "AI Agents Center", "url": "admin-shell:ai-agents-dashboard"},
            {"label": "VoiceOps", "url": None},
        ]
        context["current_module_slug"] = "ai-agents-center"
        return context


class AIDecisionApproveView(ShellContextMixin, View):
    permission_domain = "ai_agents_admin"
    permission_action = "approve"
    enforce_billing_access = False

    def post(self, request, decision_id, *args, **kwargs):
        decision = get_object_or_404(
            AgentDecision.objects.select_related("company", "site", "agent_action_proposal"),
            public_id=decision_id,
        )
        DecisionOrchestrator.approve_decision(
            decision=decision,
            approved_by=request.user,
            comment=request.POST.get("comment", ""),
        )
        return redirect(reverse("admin-shell:ai-decision-center"))


class AIDecisionRejectView(ShellContextMixin, View):
    permission_domain = "ai_agents_admin"
    permission_action = "approve"
    enforce_billing_access = False

    def post(self, request, decision_id, *args, **kwargs):
        decision = get_object_or_404(
            AgentDecision.objects.select_related("company", "site", "agent_action_proposal"),
            public_id=decision_id,
        )
        DecisionOrchestrator.reject_decision(
            decision=decision,
            rejected_by=request.user,
            comment=request.POST.get("comment", ""),
        )
        return redirect(reverse("admin-shell:ai-decision-center"))


class AIAgentProposalApproveView(ShellContextMixin, View):
    permission_domain = "ai_agents_admin"
    permission_action = "approve"
    enforce_billing_access = False

    def post(self, request, proposal_id, *args, **kwargs):
        from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService

        proposal = get_object_or_404(AgentActionProposal.objects.select_related("agent_run", "agent_run__company"), public_id=proposal_id)
        AgentCoordinatorService.approve_proposal(proposal=proposal, approved_by=request.user, company=proposal.agent_run.company)
        return redirect(reverse("admin-shell:ai-agents-proposals"))


class AIAgentProposalRejectView(ShellContextMixin, View):
    permission_domain = "ai_agents_admin"
    permission_action = "approve"
    enforce_billing_access = False

    def post(self, request, proposal_id, *args, **kwargs):
        from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService

        proposal = get_object_or_404(AgentActionProposal.objects.select_related("agent_run", "agent_run__company"), public_id=proposal_id)
        AgentCoordinatorService.reject_proposal(
            proposal=proposal,
            rejected_by=request.user,
            company=proposal.agent_run.company,
            reason=request.POST.get("reason", ""),
        )
        return redirect(reverse("admin-shell:ai-agents-proposals"))


class BillingAdminDashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/billing_dashboard.html"
    permission_domain = "billing_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_billing_dashboard_context())
        context["page_title"] = "Billing"
        context["page_description"] = "Operacao comercial da plataforma, contratos, assinaturas e faturamento recorrente."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Platform Admin", "url": None},
            {"label": "Billing", "url": None},
        ]
        context["current_module_slug"] = "billing"
        return context


class BillingPlanListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/billing_plans_list.html"
    permission_domain = "billing_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_billing_plan_context())
        context["page_title"] = "Planos"
        context["page_description"] = "Catalogo comercial da plataforma SMART360 com limites, precos e recursos habilitados."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Platform Admin", "url": None},
            {"label": "Billing", "url": "admin-shell:billing-dashboard"},
            {"label": "Planos", "url": None},
        ]
        context["current_module_slug"] = "billing"
        context["page_actions"] = [
            {"label": "Novo plano", "href": "#novo-plano", "permission_domain": "billing_admin", "permission_action": "manage"},
            {"label": "Ver contratos", "route_name": "admin-shell:billing-contracts", "permission_domain": "billing_admin", "permission_action": "view"},
            {"label": "Ver faturas", "route_name": "admin-shell:billing-invoices", "permission_domain": "billing_admin", "permission_action": "view"},
        ]
        return context


class BillingContractListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/billing_contracts_list.html"
    permission_domain = "billing_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_billing_contract_context(filters))
        context["page_title"] = "Contratos"
        context["page_description"] = "Contratos comerciais vigentes, renovacoes, suspensoes e carteira ativa da plataforma."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Platform Admin", "url": None},
            {"label": "Billing", "url": "admin-shell:billing-dashboard"},
            {"label": "Contratos", "url": None},
        ]
        context["current_module_slug"] = "billing"
        context["page_actions"] = [
            {"label": "Novo contrato", "href": "#novo-contrato", "permission_domain": "billing_admin", "permission_action": "manage"},
            {"label": "Ver planos", "route_name": "admin-shell:billing-plans", "permission_domain": "billing_admin", "permission_action": "view"},
            {"label": "Exportar carteira", "href": "#exportar-contratos", "permission_domain": "billing_admin", "permission_action": "export"},
        ]
        return context


class BillingContractDetailView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/billing_contract_detail.html"
    permission_domain = "billing_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = get_contract_detail_context(self.kwargs["contract_code"])
        if payload is None:
            raise Http404("Contrato nao encontrado.")
        context.update(payload)
        contract = payload["contract"]
        context["page_actions"] = contract["page_actions"]
        context["page_title"] = contract["contract_code"]
        context["page_description"] = f"{contract['company_name']} • {contract['plan_name']}"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Platform Admin", "url": None},
            {"label": "Billing", "url": "admin-shell:billing-dashboard"},
            {"label": "Contratos", "url": "admin-shell:billing-contracts"},
            {"label": contract["contract_code"], "url": None},
        ]
        context["current_module_slug"] = "billing"
        return context


class BillingInvoiceListView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/billing_invoices_list.html"
    permission_domain = "billing_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_billing_invoice_context(filters))
        context["page_title"] = "Faturas"
        context["page_description"] = "Historico financeiro, status de cobranca e operacao de faturamento da plataforma."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Platform Admin", "url": None},
            {"label": "Billing", "url": "admin-shell:billing-dashboard"},
            {"label": "Faturas", "url": None},
        ]
        context["current_module_slug"] = "billing"
        context["page_actions"] = [
            {"label": "Ver contratos", "route_name": "admin-shell:billing-contracts", "permission_domain": "billing_admin", "permission_action": "view"},
            {"label": "Marcar pago", "href": "#marcar-pago", "permission_domain": "billing_admin", "permission_action": "manage"},
            {"label": "Exportar faturas", "href": "#exportar-faturas", "permission_domain": "billing_admin", "permission_action": "export"},
        ]
        return context


class BillingContractSuspendView(SmartSystemAccessMixin, View):
    permission_domain = "billing_admin"
    permission_action = "manage"
    resource_type = "billing_contract"
    enforce_billing_access = False
    log_permission_decision = True

    def post(self, request, contract_code):
        contract = get_object_or_404(Contract, contract_code=contract_code)
        ContractService.suspend_contract(contract=contract, reason="Suspensao manual via shell administrativo.")
        AccessAuditService.log(
            user=request.user,
            action="billing_contract_suspended",
            domain="billing_admin",
            resource_type="contract",
            resource_id=contract.contract_code,
            decision="allow",
            reason="contract suspended from shell",
        )
        return redirect("admin-shell:billing-contract-detail", contract_code=contract_code)


class BillingContractCancelView(SmartSystemAccessMixin, View):
    permission_domain = "billing_admin"
    permission_action = "manage"
    resource_type = "billing_contract"
    enforce_billing_access = False
    log_permission_decision = True

    def post(self, request, contract_code):
        contract = get_object_or_404(Contract, contract_code=contract_code)
        ContractService.cancel_contract(contract=contract, reason="Cancelamento manual via shell administrativo.")
        AccessAuditService.log(
            user=request.user,
            action="billing_contract_cancelled",
            domain="billing_admin",
            resource_type="contract",
            resource_id=contract.contract_code,
            decision="allow",
            reason="contract cancelled from shell",
        )
        return redirect("admin-shell:billing-contract-detail", contract_code=contract_code)


class BillingInvoiceMarkPaidView(SmartSystemAccessMixin, View):
    permission_domain = "billing_admin"
    permission_action = "manage"
    resource_type = "billing_invoice"
    enforce_billing_access = False
    log_permission_decision = True

    def post(self, request, invoice_number):
        invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
        payment = invoice.payments.order_by("-created_at").first()
        if payment is not None:
            PaymentService.mark_paid(payment=payment)
        else:
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = invoice.paid_at or timezone.now()
            invoice.save(update_fields=["status", "paid_at", "updated_at"])
        AccessAuditService.log(
            user=request.user,
            action="billing_invoice_marked_paid",
            domain="billing_admin",
            resource_type="invoice",
            resource_id=invoice.invoice_number,
            decision="allow",
            reason="invoice marked paid from shell",
        )
        return redirect("admin-shell:billing-invoices")


class BillingInvoiceCancelView(SmartSystemAccessMixin, View):
    permission_domain = "billing_admin"
    permission_action = "manage"
    resource_type = "billing_invoice"
    enforce_billing_access = False
    log_permission_decision = True

    def post(self, request, invoice_number):
        invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        AccessAuditService.log(
            user=request.user,
            action="billing_invoice_cancelled",
            domain="billing_admin",
            resource_type="invoice",
            resource_id=invoice.invoice_number,
            decision="allow",
            reason="invoice cancelled from shell",
        )
        return redirect("admin-shell:billing-invoices")


class ObservabilityDashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/observability_dashboard.html"
    permission_domain = "observability_admin"
    permission_action = "view"
    enforce_billing_access = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_observability_dashboard_context())
        context["page_title"] = "Observability Center"
        context["page_description"] = "Saude da plataforma, request tracing, auditoria operacional e eventos criticos."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Infraestrutura", "url": None},
            {"label": "Observability Center", "url": None},
        ]
        context["current_module_slug"] = "observability-center"
        context["page_actions"] = [
            {"label": "Health summary", "href": "/health/", "permission_domain": "observability_admin", "permission_action": "view"},
            {"label": "Liveness", "href": "/health/live/", "permission_domain": "observability_admin", "permission_action": "view"},
            {"label": "Readiness", "href": "/health/ready/", "permission_domain": "observability_admin", "permission_action": "view"},
            {"label": "API observability", "href": "/api/v1/observability/platform-summary/", "permission_domain": "observability_admin", "permission_action": "manage"},
        ]
        return context


class DashboardView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_dashboard_context(tenant_context=self.get_tenant_context(), request=self.request))
        context["page_title"] = "Executive Command Center"
        context["page_description"] = "Cockpit administrativo do ecossistema SMART360 com visao executiva, operacional e modular."
        context["breadcrumbs"] = [{"label": "Dashboard", "url": None}]
        context["current_module_slug"] = ""
        return context


class ModulePageView(ShellContextMixin, TemplateView):
    template_name = "admin_shell/module_page.html"

    @property
    def enforce_active_company_membership(self):
        return self.kwargs.get("module_slug") == "smart-system"

    def has_required_permission(self):
        module_slug = self.kwargs.get("module_slug")
        module_permission_map = {
            "smart-system": ("dashboard", "view"),
            "marketplace-technicians": ("marketplace_dashboard", "view"),
            "billing": ("billing_admin", "view"),
            "observability-center": ("observability_admin", "view"),
            "core-platform": ("users", "view"),
            "configuration-center": ("smart_system_settings", "manage"),
        }
        if module_slug in module_permission_map:
            self.permission_domain, self.permission_action = module_permission_map[module_slug]
            return super().has_required_permission()
        return True

    def get_context_data(self, **kwargs):
        module_slug = kwargs["module_slug"]
        if module_slug not in MODULE_PAGES:
            raise Http404("Modulo nao encontrado.")
        context = super().get_context_data(**kwargs)
        module_context = build_module_page_context(module_slug)
        context["module"] = module_context
        context["page_title"] = module_context["title"]
        context["page_description"] = module_context["description"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": module_context["section"], "url": None},
            {"label": module_context["title"], "url": None},
        ]
        context["current_module_slug"] = module_slug
        if module_slug == "smart-system":
            smart_context = build_smart_system_page_context(
                get_smart_system_dashboard_context(self.request, tenant_context=self.get_tenant_context()),
                "overview",
            )
            context.update(smart_context)
            context["page_title"] = "Smart System"
            context["page_description"] = "Visao geral executiva e operacional do ambiente de manutencao."
            context["breadcrumbs"] = [
                {"label": "Dashboard", "url": "admin-shell:dashboard"},
                {"label": "Smart System", "url": None},
                {"label": "Visao Geral", "url": None},
            ]
            self.template_name = "admin_shell/smart_system/overview.html"
        return context


def _pick_kpis(kpis, labels):
    by_label = {item["label"]: item for item in kpis}
    return [by_label[label].copy() for label in labels if label in by_label]


def build_smart_system_page_context(dashboard_context, page):
    context = {}
    if page == "overview":
        context["page_actions"] = [
            {"label": "Nova OS", "route_name": "admin-shell:smart-system-work-order-create", "permission_domain": "work_orders", "permission_action": "create"},
            {"label": "Nova preventiva", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Registrar falha", "route_name": "admin-shell:smart-system-failures", "permission_domain": "failures", "permission_action": "create"},
        ]
        overview_kpis = _pick_kpis(
            dashboard_context["kpis"],
            [
                "Ativos monitorados",
                "Ordens abertas",
                "OS atrasadas",
                "Preventivas do mes",
                "Backlog tecnico",
                "Disponibilidade operacional",
            ],
        )
        for kpi in overview_kpis:
            if kpi["label"] == "Ordens abertas":
                kpi["label"] = "OS abertas"
        context.update(
            {
                "filter_groups": dashboard_context["filter_groups"][:3],
                "overview_kpis": overview_kpis,
                "critical_alerts": dashboard_context["alerts"][:3],
                "recent_work_orders": dashboard_context["work_orders"][:4],
                "overview_shortcuts": [
                    {"label": "Operacao", "context": "Fila diaria, OS, agenda e Backlog de manutencao", "route_name": "admin-shell:smart-system-operations", "tone": "sky"},
                    {"label": "Engenharia & TPM", "context": "Falhas e confiabilidade, Visao por area / site / cliente e indicadores TPM", "route_name": "admin-shell:smart-system-reliability", "tone": "teal"},
                ],
            }
        )
        return context

    if page == "operations":
        context["page_actions"] = [
            {"label": "Nova OS", "route_name": "admin-shell:smart-system-work-order-create", "permission_domain": "work_orders", "permission_action": "create"},
            {"label": "Nova preventiva", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Registrar falha", "route_name": "admin-shell:smart-system-failures", "permission_domain": "failures", "permission_action": "create"},
            {"label": "Ver agenda", "route_name": "admin-shell:smart-system-scheduling", "permission_domain": "scheduling", "permission_action": "view"},
        ]
        context.update(
            {
                "operation_kpis": dashboard_context["operation_kpis"],
                "work_orders": dashboard_context["work_orders"],
                "preventive_plan": dashboard_context["preventive_plan"],
                "backlog": dashboard_context["backlog"],
                "operational_alerts": dashboard_context["alerts"][:4],
            }
        )
        return context

    context["page_actions"] = [
        {"label": "Registrar falha", "route_name": "admin-shell:smart-system-failures", "permission_domain": "failures", "permission_action": "create"},
        {"label": "Ver checklists", "route_name": "admin-shell:smart-system-checklists", "permission_domain": "checklists", "permission_action": "view"},
        {"label": "Ver preventivas", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
        {"label": "Gerar relatorio", "route_name": "admin-shell:smart-system-reports", "permission_domain": "reports", "permission_action": "view"},
    ]
    context.update(
        {
            "technical_kpis": _pick_kpis(
                dashboard_context["kpis"],
                [
                    "MTTR",
                    "MTBF",
                    "Disponibilidade operacional",
                    "Conformidade preventiva",
                    "Falhas criticas",
                    "OS atrasadas",
                ],
            ),
            "reliability": dashboard_context["reliability"],
            "preventive_plan": dashboard_context["preventive_plan"],
            "operational_health": dashboard_context["operational_health"],
            "site_status": dashboard_context["site_status"],
            "engineering_alerts": dashboard_context["alerts"][1:],
            "tpm_indicators": dashboard_context["tpm_indicators"],
        }
    )
    return context


class SmartSystemOperationsView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system/operations.html"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            build_smart_system_page_context(
                get_smart_system_dashboard_context(self.request, tenant_context=self.get_tenant_context()),
                "operations",
            )
        )
        context["page_title"] = "Smart System - Operacao"
        context["page_description"] = "Controle diario da manutencao: OS, agenda, backlog e alertas operacionais."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Operacao", "url": None},
        ]
        context["operations_chart_data"] = build_operations_chart_data(self.request)
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemReliabilityView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system/reliability.html"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            build_smart_system_page_context(
                get_smart_system_dashboard_context(self.request, tenant_context=self.get_tenant_context()),
                "reliability",
            )
        )
        context["page_title"] = "Smart System - Engenharia & TPM"
        context["page_description"] = "Analise tecnica de confiabilidade, aderencia preventiva, reincidencia e conformidade."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Engenharia & TPM", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemAssetListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_assets_list.html"
    permission_domain = "assets"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_asset_listing_context(filters, tenant_context=self.get_tenant_context()))
        context["page_title"] = "Ativos"
        context["page_description"] = "Gestao de ativos, criticidade, condicao e historico operacional."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ativos", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemAssetDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_asset_detail.html"
    permission_domain = "assets"
    permission_action = "view"
    resource_type = "asset"

    def load_scoped_resource(self):
        return get_asset_detail_context(self.kwargs["asset_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.scoped_resource
        context["asset"] = asset
        context["page_actions"] = asset["page_actions"] + [
            {
                "label": "Abrir no Copilot",
                "href": f"{reverse('admin-shell:ai-manager-copilot')}?question=Resuma o ativo {asset['code']}",
                "permission_domain": "ai_agents_admin",
                "permission_action": "view",
            }
        ]
        context["page_title"] = asset["name"]
        context["page_description"] = asset["description"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ativos", "url": "admin-shell:smart-system-assets"},
            {"label": asset["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemEquipmentModelListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_equipment_models_list.html"
    permission_domain = "assets"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = get_equipment_model_listing_context(request=self.request, tenant_context=self.get_tenant_context())
        context.update(payload)
        context["page_title"] = "Modelos de equipamento"
        context["page_description"] = "Catalogo tecnico reutilizavel para separar modelo de equipamento do inventario instalado."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Modelos de equipamento", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemEquipmentModelDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_equipment_model_detail.html"
    permission_domain = "assets"
    permission_action = "view"
    resource_type = "equipment_model"

    def load_scoped_resource(self):
        return get_equipment_model_detail_context(
            request=self.request,
            model_code=self.kwargs["model_code"],
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment_model = self.scoped_resource
        context["equipment_model"] = equipment_model
        context["page_actions"] = equipment_model["page_actions"]
        context["page_title"] = equipment_model["name"]
        context["page_description"] = f"Modelo tecnico {equipment_model['code']}"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Modelos de equipamento", "url": "admin-shell:smart-system-equipment-models"},
            {"label": equipment_model["name"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemEquipmentModelCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_equipment_model_form.html"
    form_class = SmartSystemEquipmentModelForm
    permission_domain = "assets"
    permission_action = "create"
    resource_type = "equipment_model"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo modelo de equipamento"
        context["page_description"] = "Cadastro de catalogo tecnico desacoplado do inventario operacional."
        context["form_mode"] = "create"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Modelos de equipamento", "url": "admin-shell:smart-system-equipment-models"},
            {"label": "Novo", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        model = form.save()
        messages.success(self.request, "Modelo de equipamento criado com sucesso.")
        return redirect("admin-shell:smart-system-equipment-model-detail", model_code=str(model.public_id)[:8])


class SmartSystemEquipmentModelUpdateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_equipment_model_form.html"
    form_class = SmartSystemEquipmentModelForm
    permission_domain = "assets"
    permission_action = "update"
    resource_type = "equipment_model"

    def dispatch(self, request, *args, **kwargs):
        scoped_queryset = SmartSystemScopeService.scope_queryset(EquipmentModel.objects.all(), request)
        self.object = scoped_queryset.filter(public_id__startswith=self.kwargs["model_code"]).first()
        if self.object is None:
            return self.handle_scope_denied()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar modelo de equipamento"
        context["page_description"] = self.object.name
        context["form_mode"] = "update"
        context["equipment_model"] = self.object
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Modelos de equipamento", "url": "admin-shell:smart-system-equipment-models"},
            {"label": self.object.name, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        model = form.save()
        messages.success(self.request, "Modelo de equipamento atualizado com sucesso.")
        return redirect("admin-shell:smart-system-equipment-model-detail", model_code=str(model.public_id)[:8])


class SmartSystemCustomerEquipmentListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_customer_equipments_list.html"
    permission_domain = "assets"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = get_customer_equipment_listing_context(request=self.request, tenant_context=self.get_tenant_context())
        context.update(payload)
        context["page_title"] = "Inventario operacional"
        context["page_description"] = "Equipamentos reais instalados por cliente/site com tag operacional."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Inventario operacional", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemCustomerEquipmentDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_customer_equipment_detail.html"
    permission_domain = "assets"
    permission_action = "view"
    resource_type = "customer_equipment"

    def load_scoped_resource(self):
        return get_customer_equipment_detail_context(
            request=self.request,
            equipment_code=self.kwargs["equipment_code"],
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment = self.scoped_resource
        context["customer_equipment"] = equipment
        context["page_actions"] = equipment["page_actions"]
        context["page_title"] = equipment["full_label"]
        context["page_description"] = f"Inventario {equipment['code']}"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Inventario operacional", "url": "admin-shell:smart-system-customer-equipments"},
            {"label": equipment["customer_tag"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemCustomerEquipmentCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_customer_equipment_form.html"
    form_class = SmartSystemCustomerEquipmentForm
    permission_domain = "assets"
    permission_action = "create"
    resource_type = "customer_equipment"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo equipamento do cliente"
        context["page_description"] = "Cadastro de inventario real para operação, preventiva e rastreabilidade."
        context["form_mode"] = "create"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Inventario operacional", "url": "admin-shell:smart-system-customer-equipments"},
            {"label": "Novo", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        equipment = form.save()
        messages.success(self.request, "Equipamento do cliente criado com sucesso.")
        return redirect("admin-shell:smart-system-customer-equipment-detail", equipment_code=str(equipment.public_id)[:8])


class SmartSystemCustomerEquipmentUpdateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_customer_equipment_form.html"
    form_class = SmartSystemCustomerEquipmentForm
    permission_domain = "assets"
    permission_action = "update"
    resource_type = "customer_equipment"

    def dispatch(self, request, *args, **kwargs):
        scoped_queryset = SmartSystemScopeService.scope_queryset(CustomerEquipment.objects.all(), request)
        self.object = scoped_queryset.filter(public_id__startswith=self.kwargs["equipment_code"]).first()
        if self.object is None:
            return self.handle_scope_denied()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar equipamento do cliente"
        context["page_description"] = self.object.customer_tag
        context["form_mode"] = "update"
        context["customer_equipment_obj"] = self.object
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Inventario operacional", "url": "admin-shell:smart-system-customer-equipments"},
            {"label": self.object.customer_tag, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        equipment = form.save()
        messages.success(self.request, "Equipamento do cliente atualizado com sucesso.")
        return redirect("admin-shell:smart-system-customer-equipment-detail", equipment_code=str(equipment.public_id)[:8])


class SmartSystemCustomerListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_customers_list.html"
    permission_domain = "assets"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_customer_listing_context(request=self.request))
        context["page_title"] = "Clientes / Sites"
        context["page_description"] = "Cadastre clientes, unidades, departamentos e locais operacionais."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Clientes / Sites", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemCustomerCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_customer_form.html"
    form_class = SmartSystemMaintenanceClientForm
    permission_domain = "assets"
    permission_action = "create"
    resource_type = "maintenance_client"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo cliente"
        context["page_description"] = "Cadastro operacional de empresa contratante."
        context["form_mode"] = "create"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Clientes / Sites", "url": "admin-shell:smart-system-customers"},
            {"label": "Novo cliente", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        avail = TenantScopeService.get_available_companies(self.request.user)
        context["saas_company_count"] = len(avail)
        context["saas_companies_dashboard_url"] = reverse("admin-shell:dashboard-companies")
        context["saas_companies_create_url"] = reverse("admin-shell:dashboard-company-create")
        context["can_manage_saas_companies_shell"] = user_can_create_saas_company(self.request.user)
        return context

    def form_valid(self, form):
        form.save()
        if getattr(form, "_principal_site_created", False):
            messages.success(
                self.request,
                "Cliente cadastrado com sucesso. Unidade principal criada automaticamente.",
            )
        else:
            messages.success(self.request, "Cliente cadastrado com sucesso.")
        return redirect("admin-shell:smart-system-customers")


class SmartSystemCustomerDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_customer_detail.html"
    permission_domain = "assets"
    permission_action = "view"
    resource_type = "maintenance_client"

    def load_scoped_resource(self):
        return get_customer_detail_context(request=self.request, customer_code=self.kwargs["customer_code"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["customer"]["name"]
        context["page_description"] = "Detalhes de cliente e unidades operacionais."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Clientes / Sites", "url": "admin-shell:smart-system-customers"},
            {"label": payload["customer"]["name"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemCustomerUpdateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_customer_form.html"
    form_class = SmartSystemMaintenanceClientForm
    permission_domain = "assets"
    permission_action = "update"
    resource_type = "maintenance_client"

    def dispatch(self, request, *args, **kwargs):
        self.object = SmartSystemScopeService.scope_queryset(MaintenanceClient.objects.all(), request).filter(
            public_id__startswith=self.kwargs["customer_code"]
        ).first()
        if self.object is None:
            return self.handle_scope_denied()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar cliente"
        context["page_description"] = self.object.display_name
        context["form_mode"] = "update"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Clientes / Sites", "url": "admin-shell:smart-system-customers"},
            {"label": self.object.display_name, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Cliente atualizado com sucesso.")
        return redirect("admin-shell:smart-system-customers")


class SmartSystemSiteCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_site_form.html"
    form_class = SmartSystemOperationalSiteForm
    permission_domain = "assets"
    permission_action = "create"
    resource_type = "operational_site"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo site/unidade"
        context["page_description"] = "Cadastro de unidade operacional para cliente."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Clientes / Sites", "url": "admin-shell:smart-system-customers"},
            {"label": "Novo site/unidade", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Site/unidade criado com sucesso.")
        return redirect("admin-shell:smart-system-customers")


class SmartSystemSchedulingDashboardView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_scheduling_dashboard.html"
    permission_domain = "scheduling"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        blocked = self.require_active_company_context()
        if blocked is not None:
            return blocked
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requested_date = self.request.GET.get("date")
        date_value = timezone.datetime.strptime(requested_date, "%Y-%m-%d").date() if requested_date else timezone.localdate()
        context.update(get_scheduling_dashboard_context(tenant_context=self.get_tenant_context(), user=self.request.user, date_value=date_value))
        context["page_title"] = "Agenda & rotas"
        context["page_description"] = "Carga operacional, conflitos, visitas nao alocadas e sequencia sugerida."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Agenda & Rotas", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["page_actions"] = [
            {
                "label": "Copilot da agenda",
                "href": f"{reverse('admin-shell:ai-manager-copilot')}?source=scheduling&question=Quais tecnicos estao sobrecarregados amanha?",
                "permission_domain": "ai_agents_admin",
                "permission_action": "view",
            },
            {"label": "Nao alocadas", "route_name": "admin-shell:smart-system-unassigned-visits", "permission_domain": "scheduling", "permission_action": "view"},
        ]
        return context


class SmartSystemScheduleCalendarView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_schedule_calendar.html"
    permission_domain = "scheduling"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        blocked = self.require_active_company_context()
        if blocked is not None:
            return blocked
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requested_date = self.request.GET.get("date")
        date_value = timezone.datetime.strptime(requested_date, "%Y-%m-%d").date() if requested_date else timezone.localdate()
        context.update(get_schedule_calendar_context(tenant_context=self.get_tenant_context(), user=self.request.user, date_value=date_value))
        context["page_title"] = "Calendario operacional"
        context["page_description"] = "Visao semanal de visitas, cargas e restricoes de atendimento."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Agenda & Rotas", "url": "admin-shell:smart-system-scheduling"},
            {"label": "Calendario", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemTechnicianAgendaView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_technician_agenda.html"
    permission_domain = "scheduling"
    permission_action = "view"
    resource_type = "technician_schedule"

    def get(self, request, *args, **kwargs):
        blocked = self.require_active_company_context()
        if blocked is not None:
            return blocked
        return super().get(request, *args, **kwargs)

    def load_scoped_resource(self):
        requested_date = self.request.GET.get("date")
        date_value = timezone.datetime.strptime(requested_date, "%Y-%m-%d").date() if requested_date else timezone.localdate()
        return get_technician_agenda_context(
            tenant_context=self.get_tenant_context(),
            user=self.request.user,
            technician_id=self.kwargs["technician_id"],
            date_value=date_value,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        technician_name = self.scoped_resource["technician"].display_name or self.scoped_resource["technician"].email
        context["page_title"] = f"Agenda de {technician_name}"
        context["page_description"] = "Sequencia de rota, horario sugerido e carga diaria do tecnico."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Agenda & Rotas", "url": "admin-shell:smart-system-scheduling"},
            {"label": technician_name, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemUnassignedVisitsView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_unassigned_visits.html"
    permission_domain = "scheduling"
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        blocked = self.require_active_company_context()
        if blocked is not None:
            return blocked
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requested_date = self.request.GET.get("date")
        date_value = timezone.datetime.strptime(requested_date, "%Y-%m-%d").date() if requested_date else timezone.localdate()
        context.update(get_unassigned_visits_context(tenant_context=self.get_tenant_context(), user=self.request.user, date_value=date_value))
        context["page_title"] = "Visitas nao alocadas"
        context["page_description"] = "Carteira operacional sem tecnico definido, pronta para distribuicao."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Agenda & Rotas", "url": "admin-shell:smart-system-scheduling"},
            {"label": "Nao alocadas", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPartListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_parts_list.html"
    permission_domain = "inventory"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_part_listing_context(filters, tenant_context=self.get_tenant_context()))
        # If DB parts exist, prefer database-backed listing
        part_qs = SmartSystemScopeService.scope_queryset(__import__("apps.smart_system.models", fromlist=["Part"]).Part.objects.select_related("company","operational_site"), self.request)
        if part_qs.exists():
            mapped = []
            for p in part_qs.order_by("company__name","code"):
                mapped.append(
                    {
                        "code": str(p.public_id)[:8].upper(),
                        "name": p.name,
                        "description": p.description,
                        "category": p.category or "-",
                        "stock_current": float(p.current_stock),
                        "stock_min": float(p.minimum_stock),
                        "location": p.location or "-",
                        "supplier": p.primary_supplier or "-",
                        "status": p.get_status_display(),
                        "status_slug": p.status,
                        "is_low_stock": float(p.current_stock) <= float(p.minimum_stock),
                        "is_critical_stock": float(p.current_stock) == 0 or float(p.current_stock) < float(p.minimum_stock),
                    }
                )
            context["parts"] = mapped
        context["page_title"] = "Pecas e Sobressalentes"
        context["page_description"] = "Gestao de estoque de manutencao, sobressalentes e itens criticos de operacao."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Pecas", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPartDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_part_detail.html"
    permission_domain = "inventory"
    permission_action = "view"
    resource_type = "part"

    def load_scoped_resource(self):
        return get_part_detail_context(self.kwargs["part_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        part = self.scoped_resource
        context["part"] = part
        context["page_actions"] = part["page_actions"]
        context["page_title"] = part["code"]
        context["page_description"] = part["name"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Pecas", "url": "admin-shell:smart-system-parts"},
            {"label": part["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPartCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_part_form.html"
    form_class = SmartSystemPartForm
    permission_domain = "inventory"
    permission_action = "create"
    resource_type = "part"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nova peça"
        context["page_description"] = "Cadastro operacional de peças e sobressalentes."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Pecas", "url": "admin-shell:smart-system-parts"},
            {"label": "Nova peca", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        company = self.get_tenant_context().get("company")
        part = form.save(commit=False)
        if company:
            part.company = company
        part.save()
        messages.success(self.request, "Peça criada com sucesso.")
        return redirect("admin-shell:smart-system-parts")


class SmartSystemPartUpdateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_part_form.html"
    form_class = SmartSystemPartForm
    permission_domain = "inventory"
    permission_action = "update"
    resource_type = "part"

    def dispatch(self, request, *args, **kwargs):
        Part = __import__("apps.smart_system.models", fromlist=["Part"]).Part
        self.object = SmartSystemScopeService.scope_queryset(Part.objects.all(), request).filter(public_id__startswith=kwargs["part_code"]).first()
        if self.object is None:
            return self.handle_scope_denied()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_tenant_context()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar peça"
        context["page_description"] = self.object.name
        context["form_mode"] = "update"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Pecas", "url": "admin-shell:smart-system-parts"},
            {"label": self.object.code, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        part = form.save(commit=False)
        part.save()
        messages.success(self.request, "Peça atualizada com sucesso.")
        return redirect("admin-shell:smart-system-parts")


class SmartSystemPartDeactivateView(CMMSOperationalShellMixin, View):
    permission_domain = "inventory"
    permission_action = "update"
    resource_type = "part"

    def get(self, request, *args, **kwargs):
        Part = __import__("apps.smart_system.models", fromlist=["Part"]).Part
        part = SmartSystemScopeService.scope_queryset(Part.objects.all(), request).filter(public_id__startswith=kwargs["part_code"]).first()
        if part is None:
            messages.warning(request, "Peça não encontrada.")
            return redirect("admin-shell:smart-system-parts")
        part.status = Part.Status.INACTIVE
        part.save(update_fields=["status", "updated_at"])
        messages.success(request, "Peça desativada.")
        return redirect("admin-shell:smart-system-parts")


class SmartSystemStockMovementView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_stock_movements.html"
    permission_domain = "inventory"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_stock_movement_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Movimentacao de Estoque"
        context["page_description"] = "Entradas, saidas e ajustes manuais da operacao MRO do Smart System."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Pecas", "url": "admin-shell:smart-system-parts"},
            {"label": "Movimentacao", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemReportListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_reports_list.html"
    permission_domain = "reports"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_report_listing_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Relatorios Tecnicos"
        context["page_description"] = "Geracao, historico e exportacao de PDFs tecnicos do Smart System."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Relatorios", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemReportPreviewView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_report_preview.html"
    permission_domain = "reports"
    permission_action = "view"
    resource_type = "report"

    def load_scoped_resource(self):
        return get_report_preview_context(
            self.kwargs["report_type"],
            self.kwargs["reference_code"],
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["print_mode"] = self.request.GET.get("print") == "1"
        context["page_title"] = payload["report"]["report_code"]
        context["page_description"] = payload["report"]["document_type"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Relatorios", "url": "admin-shell:smart-system-reports"},
            {"label": payload["report"]["report_code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemReportDownloadView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "reports"
    permission_action = "export"
    resource_type = "report"
    log_permission_decision = True

    def get(self, request, report_type, reference_code):
        try:
            payload = generate_report_pdf(
                report_type,
                reference_code,
                tenant_context=build_shell_tenant_context(request),
            )
        except RuntimeError as exc:
            return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")
        if payload is None:
            return self.handle_scope_denied()
        AccessAuditService.log(
            user=request.user,
            action="report_exported",
            domain="reports",
            resource_type=report_type,
            resource_id=reference_code,
            decision="allow",
            reason="download allowed",
            metadata={"filename": payload["filename"]},
        )
        response = HttpResponse(payload["bytes"], content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{payload["filename"]}"'
        return response


class SmartSystemQuoteListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_quotes_list.html"
    permission_domain = "quotes"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_quote_listing_context(self.request, tenant_context=self.get_tenant_context(), filters=filters))
        context["page_title"] = "Orcamentos Tecnicos"
        context["page_description"] = "Pecas, mao de obra, envio ao cliente e decisao comercial por OS."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Orcamentos", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemQuoteDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_quote_detail.html"
    permission_domain = "quotes"
    permission_action = "view"
    resource_type = "service_quote"

    def load_scoped_resource(self):
        return get_quote_detail_context(self.request, self.kwargs["quote_number"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["page_title"] = self.scoped_resource["quote"].quote_number
        context["page_description"] = f"Orcamento vinculado a {self.scoped_resource['quote'].work_order.order_number}"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Orcamentos", "url": "admin-shell:smart-system-quotes"},
            {"label": self.scoped_resource["quote"].quote_number, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemQuoteSendView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "quotes"
    permission_action = "send"
    resource_type = "service_quote"
    log_permission_decision = True

    def post(self, request, quote_number):
        payload = get_quote_detail_context(request, quote_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        ServiceQuoteService.send_quote(quote=payload["quote"], user=request.user)
        return redirect("admin-shell:smart-system-quote-detail", quote_number=quote_number)


class SmartSystemQuoteApproveView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "quotes"
    permission_action = "approve"
    resource_type = "service_quote"
    log_permission_decision = True

    def post(self, request, quote_number):
        payload = get_quote_detail_context(request, quote_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        ServiceQuoteService.approve_quote(
            quote=payload["quote"],
            approver_name=request.user.display_name or request.user.email,
            approver_user=request.user,
            notes=request.POST.get("approval_notes", ""),
        )
        return redirect("admin-shell:smart-system-quote-detail", quote_number=quote_number)


class SmartSystemQuoteRejectView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "quotes"
    permission_action = "reject"
    resource_type = "service_quote"
    log_permission_decision = True

    def post(self, request, quote_number):
        payload = get_quote_detail_context(request, quote_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        ServiceQuoteService.reject_quote(
            quote=payload["quote"],
            approver_name=request.user.display_name or request.user.email,
            approver_user=request.user,
            reason=request.POST.get("rejection_reason", ""),
        )
        return redirect("admin-shell:smart-system-quote-detail", quote_number=quote_number)


class SmartSystemContractListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_contracts_list.html"
    permission_domain = "maintenance_contracts"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_contract_listing_context(self.request, tenant_context=self.get_tenant_context(), filters=filters))
        context["page_title"] = "Contratos Recorrentes"
        context["page_description"] = "Gestao de contratos de manutencao, recorrencia preventiva e cobranca continua."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Contratos", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemContractDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_contract_detail.html"
    permission_domain = "maintenance_contracts"
    permission_action = "view"
    resource_type = "maintenance_contract"

    def load_scoped_resource(self):
        return get_contract_detail_context(self.request, self.kwargs["contract_number"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.scoped_resource)
        context["page_title"] = self.scoped_resource["contract"].contract_number
        context["page_description"] = f"Contrato de {self.scoped_resource['contract'].client.display_name}"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Contratos", "url": "admin-shell:smart-system-contracts"},
            {"label": self.scoped_resource["contract"].contract_number, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["page_actions"] = list(context.get("page_actions", [])) + [
            {
                "label": "Abrir no Copilot",
                "href": f"{reverse('admin-shell:ai-manager-copilot')}?contract={self.scoped_resource['contract'].public_id}",
                "permission_domain": "ai_agents_admin",
                "permission_action": "view",
            }
        ]
        return context


class SmartSystemContractActivateView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "maintenance_contracts"
    permission_action = "manage"
    resource_type = "maintenance_contract"
    log_permission_decision = True

    def post(self, request, contract_number):
        payload = get_contract_detail_context(request, contract_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        MaintenanceContractService.activate_contract(contract=payload["contract"], user=request.user)
        return redirect("admin-shell:smart-system-contract-detail", contract_number=contract_number)


class SmartSystemContractSuspendView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "maintenance_contracts"
    permission_action = "manage"
    resource_type = "maintenance_contract"
    log_permission_decision = True

    def post(self, request, contract_number):
        payload = get_contract_detail_context(request, contract_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        MaintenanceContractService.suspend_contract(
            contract=payload["contract"],
            user=request.user,
            reason=request.POST.get("reason", ""),
        )
        return redirect("admin-shell:smart-system-contract-detail", contract_number=contract_number)


class SmartSystemContractGeneratePreventivesView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "maintenance_contracts"
    permission_action = "generate"
    resource_type = "maintenance_contract"
    log_permission_decision = True

    def post(self, request, contract_number):
        payload = get_contract_detail_context(request, contract_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        MaintenanceContractService.generate_due_preventives(contract=payload["contract"], generated_by=request.user)
        return redirect("admin-shell:smart-system-contract-detail", contract_number=contract_number)


class SmartSystemContractGenerateBillingView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "maintenance_contracts"
    permission_action = "generate"
    resource_type = "maintenance_contract"
    log_permission_decision = True

    def post(self, request, contract_number):
        payload = get_contract_detail_context(request, contract_number, tenant_context=build_shell_tenant_context(request))
        if payload is None:
            return self.handle_scope_denied()
        MaintenanceContractService.generate_billing_cycle(contract=payload["contract"], generated_by=request.user)
        return redirect("admin-shell:smart-system-contract-detail", contract_number=contract_number)


class SmartSystemWorkOrderListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_work_orders_list.html"
    permission_domain = "work_orders"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {key: value for key, value in self.request.GET.items() if value}
        context.update(get_work_order_listing_context(self.request, filters=filters, tenant_context=self.get_tenant_context()))
        context["page_title"] = "Ordens de Servico"
        context["page_description"] = "Gestao operacional de corretivas, preventivas, inspecoes e intervencoes tecnicas."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ordens de Servico", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemWorkOrderCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_work_order_create.html"
    form_class = CorrectiveServiceOrderForm
    permission_domain = "work_orders"
    permission_action = "create"
    resource_type = "work_order"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ctx = build_corrective_work_order_create_context(self.request)
        kwargs["request"] = self.request
        kwargs["asset_queryset"] = ctx["assets"]
        kwargs["user_queryset"] = ctx["assignable_users"]
        self._wo_create_ctx = ctx
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = getattr(self, "_wo_create_ctx", None) or build_corrective_work_order_create_context(self.request)
        context["no_assets"] = ctx["asset_count"] == 0
        context["page_title"] = "Nova OS corretiva"
        context["page_description"] = "Abertura de ordem de servico corretiva no escopo ativo (cliente / site)."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ordens de Servico", "url": "admin-shell:smart-system-work-orders"},
            {"label": "Nova corretiva", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["page_actions"] = [
            {"label": "Voltar a lista", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
        ]
        return context

    def form_valid(self, form):
        ctx_assets = build_corrective_work_order_create_context(self.request)
        if ctx_assets["asset_count"] == 0:
            messages.error(self.request, "Nao ha ativos disponiveis no escopo para abrir uma OS.")
            return self.form_invalid(form)

        asset = form.cleaned_data["asset"]
        if not ctx_assets["assets"].filter(pk=asset.pk).exists():
            form.add_error(None, "O ativo selecionado nao esta mais no escopo.")
            return super().form_invalid(form)

        client = asset.operational_site.maintenance_client
        if client is None:
            form.add_error(None, "O ativo nao possui cliente de manutencao configurado no site.")
            return super().form_invalid(form)

        prio = form.cleaned_data["priority"]
        if prio == ServiceOrder.Priority.URGENT and not getattr(client, "company_id", None):
            prio = ServiceOrder.Priority.HIGH

        data = {
            "client": client,
            "operational_site": asset.operational_site,
            "asset": asset,
            "maintenance_type": ServiceOrder.MaintenanceType.CORRECTIVE,
            "priority": prio,
            "status": ServiceOrder.Status.OPEN,
            "source": ServiceOrder.Source.MANUAL,
            "title": form.cleaned_data["title"].strip(),
            "description": (form.cleaned_data.get("description") or "").strip(),
            "notes": (form.cleaned_data.get("notes") or "").strip(),
            "requested_by": (form.cleaned_data.get("requested_by") or "").strip(),
            "scheduled_start": form.cleaned_data.get("scheduled_start"),
            "scheduled_end": form.cleaned_data.get("scheduled_end"),
        }
        assigned = form.cleaned_data.get("assigned_to")
        if assigned:
            data["assigned_to"] = assigned
        so = ServiceOrderService.create_service_order(user=self.request.user, validated_data=data)
        messages.success(self.request, f"OS {so.order_number} criada com sucesso.")
        return redirect("admin-shell:smart-system-work-order-detail", order_code=so.order_number)


class SmartSystemWorkOrderPreventiveCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_work_order_create_preventive.html"
    form_class = PreventiveServiceOrderForm
    permission_domain = "work_orders"
    permission_action = "create"
    resource_type = "work_order"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ctx = build_preventive_work_order_create_context(self.request)
        kwargs["request"] = self.request
        kwargs["maintenance_plan_queryset"] = ctx["maintenance_plans"]
        kwargs["asset_queryset"] = scoped_assets_for_corrective_order(self.request)
        kwargs["user_queryset"] = ctx["assignable_users"]
        self._wo_preventive_ctx = ctx
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        ctx = getattr(self, "_wo_preventive_ctx", None) or build_preventive_work_order_create_context(self.request)
        raw = self.request.GET.get("maintenance_plan")
        if raw:
            try:
                pk = int(raw)
                if ctx["maintenance_plans"].filter(pk=pk).exists():
                    initial["maintenance_plan"] = pk
            except (TypeError, ValueError):
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = getattr(self, "_wo_preventive_ctx", None) or build_preventive_work_order_create_context(self.request)
        context["no_plans"] = ctx["plan_count"] == 0
        context["page_title"] = "Nova OS preventiva"
        context["page_description"] = "Geracao de ordem de servico preventiva a partir de plano de manutencao no escopo ativo."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ordens de Servico", "url": "admin-shell:smart-system-work-orders"},
            {"label": "Nova preventiva", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["page_actions"] = [
            {"label": "Voltar a lista", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Nova OS corretiva", "route_name": "admin-shell:smart-system-work-order-create", "permission_domain": "work_orders", "permission_action": "create"},
        ]
        return context

    def form_valid(self, form):
        ctx_plans = build_preventive_work_order_create_context(self.request)
        if ctx_plans["plan_count"] == 0:
            messages.error(self.request, "Nao ha planos preventivos no escopo para gerar uma OS.")
            return self.form_invalid(form)

        plan = form.cleaned_data["maintenance_plan"]
        asset = form.cleaned_data["asset"]
        if not ctx_plans["maintenance_plans"].filter(pk=plan.pk).exists():
            form.add_error(None, "O plano selecionado nao esta mais no escopo.")
            return super().form_invalid(form)
        if not scoped_assets_for_corrective_order(self.request).filter(pk=asset.pk).exists():
            form.add_error(None, "O ativo selecionado nao esta mais no escopo.")
            return super().form_invalid(form)

        client, site = maintenance_plan_client_and_site(plan)
        if client is None or site is None:
            form.add_error(None, "Nao foi possivel resolver cliente ou site operacional para este plano.")
            return super().form_invalid(form)

        start = form.cleaned_data["scheduled_start"]
        now = timezone.now()
        status = ServiceOrder.Status.SCHEDULED if start and start > now else ServiceOrder.Status.OPEN
        title = (form.cleaned_data.get("title") or "").strip() or f"Preventiva: {plan.name}"

        prio = form.cleaned_data["priority"]
        if prio == ServiceOrder.Priority.URGENT and not getattr(client, "company_id", None):
            prio = ServiceOrder.Priority.HIGH

        data = {
            "client": client,
            "operational_site": site,
            "asset": asset,
            "maintenance_plan": plan,
            "maintenance_type": ServiceOrder.MaintenanceType.PREVENTIVE,
            "source": ServiceOrder.Source.PLAN,
            "status": status,
            "title": title[:180],
            "description": (plan.description or "").strip()[:8000],
            "priority": prio,
            "scheduled_start": start,
            "scheduled_end": form.cleaned_data.get("scheduled_end"),
            "notes": (form.cleaned_data.get("notes") or "").strip(),
        }
        assigned = form.cleaned_data.get("assigned_to")
        if assigned:
            data["assigned_to"] = assigned
        so = ServiceOrderService.create_service_order(user=self.request.user, validated_data=data)
        messages.success(self.request, f"OS preventiva {so.order_number} criada com sucesso.")
        return redirect("admin-shell:smart-system-work-order-detail", order_code=so.order_number)


class SmartSystemWorkOrderDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_work_order_detail.html"
    permission_domain = "work_orders"
    permission_action = "view"
    resource_type = "work_order"

    def load_scoped_resource(self):
        return get_work_order_detail_context(
            self.kwargs["order_code"],
            request=self.request,
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.scoped_resource
        context["work_order"] = order
        context["page_actions"] = order["page_actions"]
        context["page_title"] = order["code"]
        context["page_description"] = order["title"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ordens de Servico", "url": "admin-shell:smart-system-work-orders"},
            {"label": order["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemWorkOrderExecutionView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_work_order_execution.html"
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "work_order_execution"

    def load_scoped_resource(self):
        return get_work_order_execution_context(
            self.kwargs["order_code"],
            request=self.request,
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["technician_signature_form"] = TechnicianServiceSignatureForm(
            initial={"signer_name": self.request.user.display_name or self.request.user.full_name or self.request.user.email}
        )
        context["client_signature_form"] = ClientServiceSignatureForm()
        context["signature_error"] = self.request.GET.get("signature_error", "")
        context["page_title"] = payload["execution"]["execution_code"]
        context["page_description"] = payload["work_order"]["title"]
        context["page_actions"] = payload["execution"]["page_actions"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Ordens de Servico", "url": "admin-shell:smart-system-work-orders"},
            {"label": payload["work_order"]["code"], "url": "admin-shell:smart-system-work-order-detail", "route_kwargs": {"order_code": payload["work_order"]["code"]}},
            {"label": "Execucao", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemWorkOrderExecutionStartView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "work_order_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        AccessAuditService.log(
            user=request.user,
            action="work_order_execution_started",
            domain="work_execution",
            resource_type="work_order",
            resource_id=order_code,
            decision="allow",
            reason="manual start from shell",
        )
        return post_service_order_named_transition(request=request, order_code=order_code, transition="start")


class SmartSystemWorkOrderExecutionSaveView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "work_order_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        AccessAuditService.log(
            user=request.user,
            action="work_order_execution_progress_saved",
            domain="work_execution",
            resource_type="work_order",
            resource_id=order_code,
            decision="allow",
            reason="progress saved from shell",
        )
        return post_service_order_progress_notes(request=request, order_code=order_code)


class SmartSystemWorkOrderTechnicianSignatureView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "service_signatures"
    permission_action = "capture"
    resource_type = "work_order_signature"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        result, error_response = _capture_service_signature_or_error(
            request=request,
            order_code=order_code,
            signature_kind="technician",
        )
        if error_response:
            return error_response
        AccessAuditService.log(
            user=request.user,
            action="work_order_technician_signature_saved",
            domain="service_signatures",
            decision="allow",
            resource_type="work_order",
            resource_id=order_code,
            reason="technician signature saved from shell",
            metadata={"signature_id": str(result.signature.public_id)},
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:smart-system-work-order-execution", order_code=order_code)


class SmartSystemWorkOrderClientSignatureView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "service_signatures"
    permission_action = "capture"
    resource_type = "work_order_signature"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        result, error_response = _capture_service_signature_or_error(
            request=request,
            order_code=order_code,
            signature_kind="client",
        )
        if error_response:
            return error_response
        AccessAuditService.log(
            user=request.user,
            action="work_order_client_signature_saved",
            domain="service_signatures",
            decision="allow",
            resource_type="work_order",
            resource_id=order_code,
            reason="client signature or missing reason saved from shell",
            metadata={"signature_id": str(result.signature.public_id)},
            company=self.get_current_company(),
            site=self.get_current_site(),
        )
        return redirect("admin-shell:smart-system-work-order-execution", order_code=order_code)


class SmartSystemWorkOrderExecutionCompleteView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "close"
    resource_type = "work_order"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        service_order = ServiceSignatureService.get_service_order(order_code)
        signature_summary = ServiceSignatureService.get_signature_summary(service_order)
        AccessAuditService.log(
            user=request.user,
            action="work_order_execution_completed",
            domain="work_orders",
            resource_type="work_order",
            resource_id=order_code,
            decision="allow",
            reason="service order closed via shell",
            metadata={
                "has_technician_signature": signature_summary.get("has_technician_signature"),
                "has_client_signature": signature_summary.get("has_client_signature"),
                "missing_reason_recorded": signature_summary.get("missing_reason_recorded"),
            },
        )
        return post_service_order_complete(request=request, order_code=order_code)


class SmartSystemWorkOrderTransitionView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "update"
    resource_type = "work_order"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        return post_service_order_transition(request=request, order_code=order_code)


class SmartSystemWorkOrderWorkLogView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_orders"
    permission_action = "update"
    resource_type = "work_order"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        return post_service_order_worklog(request=request, order_code=order_code)


class SmartSystemWorkOrderChecklistSaveView(SmartSystemOperationalRouteMixin, SmartSystemAccessMixin, View):
    permission_domain = "work_execution"
    permission_action = "execute"
    resource_type = "work_order_execution"
    log_permission_decision = True

    def post(self, request, order_code):
        if get_work_order_detail_context(
            order_code,
            request=request,
            tenant_context=build_shell_tenant_context(request),
        ) is None:
            return self.handle_scope_denied()
        return post_service_order_checklist_responses(request=request, order_code=order_code)


class SmartSystemPreventiveListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_preventives_list.html"
    permission_domain = "preventive_plans"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_preventive_listing_context(filters, tenant_context=self.get_tenant_context()))
        context["page_title"] = "Planos Preventivos"
        context["page_description"] = "Gestao de recorrencia, agenda, cobertura e execucao da manutencao planejada."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Planos Preventivos", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPreventiveScheduleView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_preventives_schedule.html"
    permission_domain = "preventive_plans"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_preventive_schedule_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Agenda Preventiva"
        context["page_description"] = "Agenda operacional com atividades preventivas do dia, semana e backlog planejado."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Planos Preventivos", "url": "admin-shell:smart-system-preventives"},
            {"label": "Agenda", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPreventiveCalendarView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_preventives_calendar.html"
    permission_domain = "preventive_plans"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_preventive_calendar_context(tenant_context=self.get_tenant_context()))
        context["page_title"] = "Calendario Preventivo"
        context["page_description"] = "Visualizacao mensal das preventivas programadas, vencidas, concluidas e criticas."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Planos Preventivos", "url": "admin-shell:smart-system-preventives"},
            {"label": "Calendario", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemPreventiveDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_preventive_detail.html"
    permission_domain = "preventive_plans"
    permission_action = "view"
    resource_type = "preventive_plan"

    def load_scoped_resource(self):
        return get_preventive_detail_context(self.kwargs["plan_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.scoped_resource
        context["preventive_plan"] = plan
        context["page_actions"] = plan["page_actions"]
        context["page_title"] = plan["code"]
        context["page_description"] = plan["name"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Planos Preventivos", "url": "admin-shell:smart-system-preventives"},
            {"label": plan["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemFailureListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_failures_list.html"
    permission_domain = "failures"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_failure_listing_context(filters, tenant_context=self.get_tenant_context()))
        context["page_title"] = "Eventos de Falha"
        context["page_description"] = "Registro, analise e historico de falhas de ativos."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Eventos de Falha", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemFailureDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_failure_detail.html"
    permission_domain = "failures"
    permission_action = "view"
    resource_type = "failure_event"

    def load_scoped_resource(self):
        return get_failure_detail_context(self.kwargs["failure_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        failure = self.scoped_resource
        context["failure"] = failure
        context["page_actions"] = failure["page_actions"]
        context["page_title"] = failure["code"]
        context["page_description"] = failure["failure_mode"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Eventos de Falha", "url": "admin-shell:smart-system-failures"},
            {"label": failure["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemChecklistListView(CMMSOperationalShellMixin, TemplateView):
    template_name = "admin_shell/smart_system_checklists_list.html"
    permission_domain = "checklists"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = apply_active_scope_filters({key: value for key, value in self.request.GET.items() if value}, self.get_tenant_context())
        context.update(get_checklist_listing_context(filters, tenant_context=self.get_tenant_context()))
        # Prefer database-backed checklists when present (merge for simplicity).
        db_qs = Checklist.objects.prefetch_related("items").all()
        if db_qs.exists():
            mapped = []
            for checklist in db_qs.order_by("name"):
                mapped.append(
                    {
                        "code": checklist.public_id.hex[:8].upper(),
                        "name": checklist.name,
                        "description": checklist.description,
                        "application_label": "Geral",
                        "category": getattr(checklist, "category", "") or "-",
                        "status_slug": "active" if checklist.is_active else "inactive",
                    }
                )
            context["checklists"] = mapped
        context["page_title"] = "Checklists"
        context["page_description"] = "Cadastre rotinas tecnicas simples para equipamentos, servicos e preventivas."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemChecklistCreateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_checklist_form.html"
    form_class = SmartSystemChecklistForm
    permission_domain = "checklists"
    permission_action = "create"
    resource_type = "checklist"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo checklist"
        context["page_description"] = "Cadastro operacional simples de rotina tecnica."
        context["form_mode"] = "create"
        context["item_forms"] = [
            SmartSystemChecklistItemForm(prefix=f"item-{index}")
            for index in range(1, 7)
        ]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": "admin-shell:smart-system-checklists"},
            {"label": "Novo", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        company = self.get_tenant_context().get("company")
        site = self.get_tenant_context().get("site")
        checklist = Checklist.objects.create(
            company=company,
            operational_site=site,
            name=form.cleaned_data["name"],
            description=form.cleaned_data.get("description", ""),
            is_active=True,
        )

        ordering = 1
        for index in range(1, 7):
            item_form = SmartSystemChecklistItemForm(
                self.request.POST,
                prefix=f"item-{index}",
            )
            if not item_form.is_valid():
                continue
            description = (item_form.cleaned_data.get("description") or "").strip()
            if not description:
                continue
            response_type = item_form.cleaned_data.get("response_type") or "ok_nok"
            item_type = ChecklistItem.ItemType.BOOLEAN
            if response_type == "text":
                item_type = ChecklistItem.ItemType.TEXT
            elif response_type == "number":
                item_type = ChecklistItem.ItemType.NUMBER
            elif response_type == "yes_no":
                item_type = ChecklistItem.ItemType.CHOICE
            ChecklistItem.objects.create(
                checklist=checklist,
                title=description,
                description="",
                item_type=item_type,
                ordering=ordering,
                is_required=item_form.cleaned_data.get("required", True),
                is_active=True,
            )
            ordering += 1

        messages.success(self.request, "Checklist criado com sucesso.")
        return redirect("admin-shell:smart-system-checklists")


class SmartSystemChecklistUpdateView(CMMSOperationalShellMixin, FormView):
    template_name = "admin_shell/smart_system_checklist_form.html"
    form_class = SmartSystemChecklistForm
    permission_domain = "checklists"
    permission_action = "update"
    resource_type = "checklist"

    def dispatch(self, request, *args, **kwargs):
        self.checklist = SmartSystemScopeService.scope_queryset(Checklist.objects.all(), request).filter(
            public_id__startswith=kwargs["checklist_code"]
        ).first()
        if self.checklist is None:
            messages.warning(request, "Checklist não encontrado para edição.")
            return redirect("admin-shell:smart-system-checklists")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "name": self.checklist.name,
            "description": self.checklist.description,
            "category": "",
            "application_type": "general",
            "status": "active" if self.checklist.is_active else "inactive",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar checklist"
        context["page_description"] = self.checklist.name
        context["form_mode"] = "update"
        items = list(self.checklist.items.filter(is_active=True).order_by("ordering", "id")[:6])
        item_forms = []
        for index in range(1, 7):
            item = items[index - 1] if index - 1 < len(items) else None
            initial = {}
            if item:
                response_type = "ok_nok"
                if item.item_type == ChecklistItem.ItemType.TEXT:
                    response_type = "text"
                elif item.item_type == ChecklistItem.ItemType.NUMBER:
                    response_type = "number"
                elif item.item_type == ChecklistItem.ItemType.CHOICE:
                    response_type = "yes_no"
                initial = {
                    "description": item.title,
                    "response_type": response_type,
                    "required": item.is_required,
                }
            item_forms.append(SmartSystemChecklistItemForm(prefix=f"item-{index}", initial=initial))
        context["item_forms"] = item_forms
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": "admin-shell:smart-system-checklists"},
            {"label": self.checklist.name, "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context

    def form_valid(self, form):
        self.checklist.name = form.cleaned_data["name"]
        self.checklist.description = form.cleaned_data.get("description", "")
        self.checklist.is_active = True
        self.checklist.save(update_fields=["name", "description", "is_active", "updated_at"])

        existing_items = list(self.checklist.items.order_by("ordering", "id"))
        ordering = 1
        for index in range(1, 7):
            item_form = SmartSystemChecklistItemForm(self.request.POST, prefix=f"item-{index}")
            if not item_form.is_valid():
                continue
            description = (item_form.cleaned_data.get("description") or "").strip()
            if index - 1 < len(existing_items):
                item = existing_items[index - 1]
                if not description:
                    item.is_active = False
                    item.save(update_fields=["is_active", "updated_at"])
                    continue
            elif not description:
                continue
            response_type = item_form.cleaned_data.get("response_type") or "ok_nok"
            item_type = ChecklistItem.ItemType.BOOLEAN
            if response_type == "text":
                item_type = ChecklistItem.ItemType.TEXT
            elif response_type == "number":
                item_type = ChecklistItem.ItemType.NUMBER
            elif response_type == "yes_no":
                item_type = ChecklistItem.ItemType.CHOICE

            if index - 1 < len(existing_items):
                item = existing_items[index - 1]
                item.title = description
                item.item_type = item_type
                item.is_required = item_form.cleaned_data.get("required", True)
                item.is_active = True
                item.ordering = ordering
                item.save(update_fields=["title", "item_type", "is_required", "is_active", "ordering", "updated_at"])
            else:
                ChecklistItem.objects.create(
                    checklist=self.checklist,
                    title=description,
                    description="",
                    item_type=item_type,
                    ordering=ordering,
                    is_required=item_form.cleaned_data.get("required", True),
                    is_active=True,
                )
            ordering += 1

        messages.success(self.request, "Checklist atualizado com sucesso.")
        return redirect("admin-shell:smart-system-checklists")


class SmartSystemChecklistDeactivateView(CMMSOperationalShellMixin, View):
    permission_domain = "checklists"
    permission_action = "update"
    resource_type = "checklist"

    def get(self, request, *args, **kwargs):
        checklist = SmartSystemScopeService.scope_queryset(Checklist.objects.all(), request).filter(
            public_id__startswith=kwargs["checklist_code"]
        ).first()
        if checklist is None:
            messages.warning(request, "Checklist não encontrado para desativação.")
            return redirect("admin-shell:smart-system-checklists")
        checklist.is_active = False
        checklist.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"Checklist {checklist.name} desativado.")
        return redirect("admin-shell:smart-system-checklists")


class SmartSystemChecklistDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_checklist_detail.html"
    permission_domain = "checklists"
    permission_action = "view"
    resource_type = "checklist"

    def load_scoped_resource(self):
        return get_checklist_detail_context(self.kwargs["checklist_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        checklist = self.scoped_resource
        context["checklist"] = checklist
        context["page_actions"] = checklist["page_actions"]
        context["page_title"] = checklist["code"]
        context["page_description"] = checklist["name"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": "admin-shell:smart-system-checklists"},
            {"label": checklist["code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemChecklistExecutionView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_checklist_execution.html"
    permission_domain = "checklists"
    permission_action = "execute"
    resource_type = "checklist_execution"

    def load_scoped_resource(self):
        return get_execution_context(self.kwargs["checklist_code"], tenant_context=self.get_tenant_context())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = payload["execution"]["execution_code"]
        context["page_description"] = payload["checklist"]["name"]
        context["page_actions"] = payload["execution"]["page_actions"]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": "admin-shell:smart-system-checklists"},
            {"label": payload["checklist"]["code"], "url": "admin-shell:smart-system-checklist-detail", "route_kwargs": {"checklist_code": payload["checklist"]["code"]}},
            {"label": "Execucao", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context


class SmartSystemChecklistExecutionDetailView(ScopedResourceTemplateView):
    template_name = "admin_shell/smart_system_checklist_execution_detail.html"
    permission_domain = "checklists"
    permission_action = "view"
    resource_type = "checklist_execution"

    def load_scoped_resource(self):
        return get_execution_context(
            self.kwargs["checklist_code"],
            self.kwargs["execution_code"],
            tenant_context=self.get_tenant_context(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.scoped_resource
        context.update(payload)
        context["page_title"] = kwargs["execution_code"]
        context["page_description"] = payload["checklist"]["name"]
        context["page_actions"] = [
            {
                "label": "Iniciar nova execucao",
                "route_name": "admin-shell:smart-system-checklist-execution",
                "route_kwargs": {"checklist_code": payload["checklist"]["code"]},
                "permission_domain": "checklists",
                "permission_action": "execute",
            },
            {
                "label": "Abrir checklist",
                "route_name": "admin-shell:smart-system-checklist-detail",
                "route_kwargs": {"checklist_code": payload["checklist"]["code"]},
                "permission_domain": "checklists",
                "permission_action": "view",
            },
        ]
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Smart System", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}},
            {"label": "Checklists", "url": "admin-shell:smart-system-checklists"},
            {"label": payload["checklist"]["code"], "url": "admin-shell:smart-system-checklist-detail", "route_kwargs": {"checklist_code": payload["checklist"]["code"]}},
            {"label": kwargs["execution_code"], "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        return context
