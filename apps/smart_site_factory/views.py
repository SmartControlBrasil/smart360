from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.admin_shell.security import SmartSystemShellAccessMixin
from apps.smart_site_factory.forms import SiteOrderCreateForm, SiteProjectIntakeForm
from apps.smart_site_factory.models import ProductionTask, SiteOrder
from apps.smart_site_factory.services.order_service import ProductionService, SiteOrderService
from apps.smart_site_factory.services.site_order_lead_bridge import upsert_lead_from_site_order
from apps.smart_site_factory.services.site_order_proposal_decision import apply_proposal_approval, apply_proposal_rejection
from apps.smart_site_factory.services.site_order_proposal_email import send_site_order_proposal_email
from apps.smart_site_factory.services.site_factory_dashboard import (
    apply_dashboard_filters,
    build_kpis,
    filter_option_querysets,
    orders_by_status_series,
    pending_tasks_detail,
    recent_deliveries,
    recent_orders,
    top_commercial_packages_series,
    top_niches_series,
)
from apps.smart_site_factory.services.template_package import package_hints_map, resolve_commercial_package_for_order


ORDER_STATUS_TONES = {
    SiteOrder.Status.DRAFT: "slate",
    SiteOrder.Status.INTAKE_PENDING: "amber",
    SiteOrder.Status.IN_PRODUCTION: "sky",
    SiteOrder.Status.REVIEW: "violet",
    SiteOrder.Status.DELIVERED: "emerald",
    SiteOrder.Status.CANCELLED: "red",
}

TASK_STATUS_TONES = {
    ProductionTask.Status.TODO: "slate",
    ProductionTask.Status.IN_PROGRESS: "sky",
    ProductionTask.Status.BLOCKED: "red",
    ProductionTask.Status.DONE: "emerald",
}


class SiteFactoryShellMixin(SmartSystemShellAccessMixin):
    current_module_slug = "smart-site-factory"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_shell_context(self):
        context = super().get_shell_context()
        current_name = getattr(getattr(self.request, "resolver_match", None), "view_name", "")
        context["shell_navigation"] = self._navigation_for_site_factory(current_name)
        context["current_module_slug"] = self.current_module_slug
        return context

    def _navigation_for_site_factory(self, current_name):
        from apps.admin_shell.services.shell import get_navigation

        return get_navigation(
            current_name,
            self.current_module_slug,
            permission_map=self.get_permission_map(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_shell_context())
        return context

    def get_order_queryset(self):
        queryset = (
            SiteOrder.objects.select_related("company", "requester", "niche", "selected_template", "recommended_template")
            .prefetch_related("production_tasks")
            .order_by("-ordered_at")
        )
        tenant_company = self.get_shell_context()["shell_tenant_context"].get("company")
        if self.request.user.is_superuser:
            return queryset
        if tenant_company is not None:
            return queryset.filter(company=tenant_company)
        return queryset.filter(
            Q(requester=self.request.user)
            | Q(company__memberships__user=self.request.user, company__memberships__status="active")
        ).distinct()

    def get_order(self):
        return get_object_or_404(self.get_order_queryset(), pk=self.kwargs["pk"])

    def get_optional_relation(self, instance, relation_name):
        try:
            return getattr(instance, relation_name)
        except ObjectDoesNotExist:
            return None

    def orders_list_url(self, **params):
        base = reverse("admin-shell:site-factory-orders")
        query = {k: v for k, v in params.items() if v not in (None, "", [])}
        if not query:
            return base
        return f"{base}?{urlencode(query)}"


class SiteFactoryDashboardView(SiteFactoryShellMixin, TemplateView):
    template_name = "admin_shell/site_factory_dashboard.html"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_order_queryset()
        filtered = apply_dashboard_filters(base_qs, get_params=self.request.GET)
        order_ids = list(filtered.values_list("id", flat=True))
        options = filter_option_querysets()
        kpi = build_kpis(filtered)
        ol = self.orders_list_url
        context.update(
            {
                "page_title": "Smart Site Factory",
                "page_description": "Dashboard operacional de pedidos, briefing, producao e entregas.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": None},
                ],
                "page_actions": [
                    {"label": "Novo Projeto", "href": reverse("admin-shell:site-factory-order-new")},
                    {"label": "Lista de pedidos", "href": reverse("admin-shell:site-factory-orders")},
                ],
                "kpi": kpi,
                "kpi_cards": [
                    {
                        "label": "Projetos ativos",
                        "value": kpi["active_projects"],
                        "tone": "indigo",
                        "helper": "Nao entregues nem cancelados",
                        "href": ol(lifecycle="active"),
                    },
                    {
                        "label": "Aguardando briefing",
                        "value": kpi["awaiting_briefing"],
                        "tone": "amber",
                        "helper": "Intake pendente sem briefing salvo",
                        "href": ol(briefing="pending"),
                    },
                    {
                        "label": "Em producao",
                        "value": kpi["in_production"],
                        "tone": "sky",
                        "helper": "Pedidos em execucao",
                        "href": ol(status=SiteOrder.Status.IN_PRODUCTION),
                    },
                    {
                        "label": "Entregues",
                        "value": kpi["delivered"],
                        "tone": "emerald",
                        "helper": "Projetos concluidos",
                        "href": ol(status=SiteOrder.Status.DELIVERED),
                    },
                    {
                        "label": "Receita potencial",
                        "value": kpi["potential_revenue"],
                        "tone": "violet",
                        "helper": "Soma de pedidos ativos",
                        "href": ol(lifecycle="active"),
                        "format": "currency",
                    },
                    {
                        "label": "Tarefas pendentes",
                        "value": kpi["pending_tasks"],
                        "tone": "rose",
                        "helper": "TODO, em progresso ou bloqueadas",
                        "href": f"{reverse('admin-shell:site-factory-dashboard')}#pending-tasks",
                    },
                ],
                "recent_orders": recent_orders(filtered, limit=8),
                "recent_deliveries": recent_deliveries(order_ids, limit=8),
                "pending_tasks_rows": pending_tasks_detail(order_ids, limit=12),
                "chart_orders_by_status": orders_by_status_series(filtered),
                "chart_top_niches": top_niches_series(filtered),
                "chart_top_packages": top_commercial_packages_series(filtered),
                "status_choices": SiteOrder.Status.choices,
                "selected_status": self.request.GET.get("status", ""),
                "selected_niche": self.request.GET.get("niche", ""),
                "selected_template": self.request.GET.get("template", ""),
                "niches": options["niches"],
                "templates": options["templates"],
                "status_tones": ORDER_STATUS_TONES,
                "task_status_tones": TASK_STATUS_TONES,
            }
        )
        return context


class SiteFactoryOrderListView(SiteFactoryShellMixin, ListView):
    template_name = "admin_shell/site_factory_orders_list.html"
    context_object_name = "orders"
    paginate_by = 30
    permission_domain = "dashboard"
    permission_action = "view"

    def get_queryset(self):
        queryset = self.get_order_queryset()
        return apply_dashboard_filters(queryset, get_params=self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        options = filter_option_querysets()
        context.update(
            {
                "page_title": "Projetos Smart Site Factory",
                "page_description": "Pedidos, intake, producao e entrega dos sites em andamento.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": None},
                ],
                "page_actions": [
                    {"label": "Dashboard SSF", "href": reverse("admin-shell:site-factory-dashboard")},
                    {"label": "Novo Projeto", "href": reverse("admin-shell:site-factory-order-new")},
                ],
                "status_choices": SiteOrder.Status.choices,
                "selected_status": self.request.GET.get("status", ""),
                "selected_niche": self.request.GET.get("niche", ""),
                "selected_template": self.request.GET.get("template", ""),
                "selected_lifecycle": self.request.GET.get("lifecycle", ""),
                "selected_briefing": self.request.GET.get("briefing", ""),
                "niches": options["niches"],
                "templates": options["templates"],
                "status_tones": ORDER_STATUS_TONES,
            }
        )
        return context


class SiteFactoryOrderCreateView(SiteFactoryShellMixin, FormView):
    template_name = "admin_shell/site_factory_order_form.html"
    form_class = SiteOrderCreateForm
    permission_domain = "dashboard"
    permission_action = "view"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["tenant_context"] = self.get_shell_context()["shell_tenant_context"]
        return kwargs

    def form_valid(self, form):
        order = SiteOrderService.create_order(
            requester=self.request.user,
            validated_data=form.build_order_payload(),
        )
        messages.success(self.request, "Projeto criado com sucesso.")
        return redirect("admin-shell:site-factory-order-detail", pk=order.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        if form is not None:
            context["template_choice_hints"] = package_hints_map(form.fields["selected_template"].queryset)
        else:
            context["template_choice_hints"] = {}
        context.update(
            {
                "page_title": "Novo Projeto",
                "page_description": "Selecione nicho, template ou recomendacao automatica e registre os dados iniciais do cliente.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": "admin-shell:site-factory-orders"},
                    {"label": "Novo Projeto", "url": None},
                ],
                "page_actions": [
                    {"label": "Voltar aos Projetos", "href": reverse("admin-shell:site-factory-orders")},
                ],
            }
        )
        return context


class SiteFactoryOrderDetailView(SiteFactoryShellMixin, DetailView):
    template_name = "admin_shell/site_factory_order_detail.html"
    context_object_name = "order"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_queryset(self):
        return self.get_order_queryset().select_related("intake")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        tasks = order.production_tasks.select_related("assignee").order_by("order", "id")
        intake = self.get_optional_relation(order, "intake")
        delivery = self.get_optional_relation(order, "delivery_record")
        timeline = self._build_timeline(order, tasks, intake, delivery)
        linked_lead = None
        lead_admin_url = None
        md = order.metadata if isinstance(order.metadata, dict) else {}
        lead_pk = md.get("lead_id")
        if lead_pk is not None:
            try:
                from apps.growth_engine.models import Lead

                linked_lead = Lead.objects.filter(pk=int(lead_pk)).first()
                if linked_lead and self.request.user.is_staff:
                    lead_admin_url = reverse("admin:growth_engine_lead_change", args=[linked_lead.pk])
            except Exception:
                linked_lead = None
                lead_admin_url = None
        proposal_status = (md.get("proposal_status") or "").strip().lower()
        proposal_approved_at = md.get("proposal_approved_at", "")
        proposal_approved_by = md.get("proposal_approved_by", "")
        proposal_rejected_at = md.get("proposal_rejected_at", "")
        proposal_rejected_by = md.get("proposal_rejected_by", "")
        context.update(
            {
                "page_title": f"Projeto #{order.id}",
                "page_description": "Detalhe operacional do pedido, briefing, producao e entrega.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": "admin-shell:site-factory-orders"},
                    {"label": f"Projeto #{order.id}", "url": None},
                ],
                "page_actions": [
                    {
                        "label": "Ver proposta comercial",
                        "href": reverse("admin-shell:site-factory-order-proposal", kwargs={"pk": order.pk}),
                    },
                    {"label": "Briefing", "href": reverse("admin-shell:site-factory-order-intake", kwargs={"pk": order.pk})},
                    {"label": "Producao", "href": reverse("admin-shell:site-factory-order-tasks", kwargs={"pk": order.pk})},
                ],
                "tasks": tasks,
                "intake": intake,
                "delivery": delivery,
                "timeline": timeline,
                "order_status_tone": ORDER_STATUS_TONES.get(order.status, "slate"),
                "task_status_tones": TASK_STATUS_TONES,
                "linked_lead": linked_lead,
                "lead_admin_url": lead_admin_url,
                "commercial_status": md.get("commercial_status", ""),
                "commercial_package": resolve_commercial_package_for_order(order),
                "proposal_status": proposal_status,
                "proposal_approved_at": proposal_approved_at,
                "proposal_approved_by": proposal_approved_by,
                "proposal_rejected_at": proposal_rejected_at,
                "proposal_rejected_by": proposal_rejected_by,
            }
        )
        return context

    def _build_timeline(self, order, tasks, intake, delivery):
        items = [{"label": "Pedido criado", "meta": order.ordered_at, "tone": "indigo"}]
        if intake is not None:
            items.append({"label": "Briefing recebido", "meta": intake.updated_at, "tone": "amber"})
        if order.production_started_at:
            items.append({"label": "Producao iniciada", "meta": order.production_started_at, "tone": "sky"})
        done_count = sum(1 for task in tasks if task.status == ProductionTask.Status.DONE)
        if tasks:
            items.append({"label": f"Producao: {done_count}/{len(tasks)} tarefas concluidas", "meta": order.updated_at, "tone": "violet"})
        if delivery:
            items.append({"label": "Entrega registrada", "meta": delivery.delivered_at, "tone": "emerald"})
        return items


class SiteFactoryOrderProposalView(SiteFactoryShellMixin, DetailView):
    """Proposta comercial HTML (MVP), sem modelo persistente nem envio de email."""

    template_name = "admin_shell/site_factory_order_proposal.html"
    context_object_name = "order"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_queryset(self):
        return self.get_order_queryset().select_related(
            "intake",
            "company",
            "requester",
            "niche",
            "selected_template",
            "recommended_template",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        tasks = list(order.production_tasks.order_by("order", "id"))
        intake = self.get_optional_relation(order, "intake")
        md = order.metadata if isinstance(order.metadata, dict) else {}
        linked_lead = None
        lead_pk = md.get("lead_id")
        if lead_pk is not None:
            try:
                from apps.growth_engine.models import Lead

                linked_lead = Lead.objects.filter(pk=int(lead_pk)).first()
            except Exception:
                linked_lead = None

        proposal_status = (md.get("proposal_status") or "").strip().lower()
        proposal_approved_at = md.get("proposal_approved_at", "")
        proposal_approved_by = md.get("proposal_approved_by", "")
        proposal_rejected_at = md.get("proposal_rejected_at", "")
        proposal_rejected_by = md.get("proposal_rejected_by", "")

        now = timezone.now()
        valid_until = (now.date() + timedelta(days=7))
        commercial_package = resolve_commercial_package_for_order(order)
        fp = order.final_price or Decimal("0.00")
        if fp <= 0 and commercial_package and commercial_package.get("price_display"):
            try:
                package_price = Decimal(str(commercial_package["price_display"]))
                if package_price > 0:
                    fp = package_price
            except (InvalidOperation, TypeError, ValueError):
                pass
        half = (fp / Decimal("2")).quantize(Decimal("0.01"))
        balance = fp - half

        standard_stages = [label for _value, label in ProductionTask.Stage.choices]

        context.update(
            {
                "page_title": f"Proposta comercial — projeto #{order.id}",
                "page_description": "Documento para alinhamento com o cliente; imprima ou salve em PDF pelo navegador.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": "admin-shell:site-factory-orders"},
                    {"label": f"Projeto #{order.id}", "url": None},
                    {"label": "Proposta comercial", "url": None},
                ],
                "page_actions": [
                    {"label": "Voltar ao projeto", "href": reverse("admin-shell:site-factory-order-detail", kwargs={"pk": order.pk})},
                ],
                "commercial_package": commercial_package,
                "intake": intake,
                "production_tasks": tasks,
                "production_stage_fallback": standard_stages,
                "linked_lead": linked_lead,
                "proposal_generated_at": now,
                "proposal_valid_until": valid_until,
                "proposal_price": fp,
                "deposit_amount": half,
                "balance_amount": balance,
                "commercial_status": md.get("commercial_status", ""),
                "proposal_status": proposal_status,
                "proposal_approved_at": proposal_approved_at,
                "proposal_approved_by": proposal_approved_by,
                "proposal_rejected_at": proposal_rejected_at,
                "proposal_rejected_by": proposal_rejected_by,
            }
        )
        return context


class SiteFactoryOrderProposalApproveView(SiteFactoryShellMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        ok, msg = apply_proposal_approval(order=order, user=request.user)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("admin-shell:site-factory-order-detail", pk=order.pk)


class SiteFactoryOrderProposalRejectView(SiteFactoryShellMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        ok, msg = apply_proposal_rejection(order=order, user=request.user)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("admin-shell:site-factory-order-detail", pk=order.pk)


class SiteFactoryOrderProposalSendEmailView(SiteFactoryShellMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        ok, msg = send_site_order_proposal_email(order=order, request=request)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("admin-shell:site-factory-order-detail", pk=order.pk)


class SiteFactoryOrderCommercialOpportunityView(SiteFactoryShellMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        try:
            upsert_lead_from_site_order(order=order, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception:
            messages.error(
                request,
                "Nao foi possivel registrar a oportunidade comercial. Verifique o Growth Engine e tente novamente.",
            )
        else:
            messages.success(request, "Oportunidade comercial sincronizada com o Growth Engine.")
        return redirect("admin-shell:site-factory-order-detail", pk=order.pk)


class SiteFactoryIntakeView(SiteFactoryShellMixin, FormView):
    template_name = "admin_shell/site_factory_intake_form.html"
    form_class = SiteProjectIntakeForm
    permission_domain = "dashboard"
    permission_action = "view"

    def dispatch(self, request, *args, **kwargs):
        self.order = self.get_order()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["order"] = self.order
        kwargs["instance"] = self.get_optional_relation(self.order, "intake")
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Briefing salvo com sucesso.")
        return redirect("admin-shell:site-factory-order-detail", pk=self.order.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "order": self.order,
                "page_title": f"Briefing do Projeto #{self.order.id}",
                "page_description": "Intake comercial e criativo para orientar copy, design e desenvolvimento.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": "admin-shell:site-factory-orders"},
                    {"label": f"Projeto #{self.order.id}", "url": None},
                    {"label": "Briefing", "url": None},
                ],
                "page_actions": [
                    {"label": "Ver Projeto", "href": reverse("admin-shell:site-factory-order-detail", kwargs={"pk": self.order.pk})},
                ],
            }
        )
        return context


class SiteFactoryTaskListView(SiteFactoryShellMixin, DetailView):
    template_name = "admin_shell/site_factory_tasks.html"
    context_object_name = "order"
    permission_domain = "dashboard"
    permission_action = "view"

    def get_queryset(self):
        return self.get_order_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        context.update(
            {
                "page_title": f"Producao do Projeto #{order.id}",
                "page_description": "Controle server-side das tarefas de producao do site.",
                "breadcrumbs": [
                    {"label": "Dashboard", "url": "admin-shell:dashboard"},
                    {"label": "Smart Site Factory", "url": "admin-shell:site-factory-dashboard"},
                    {"label": "Projetos", "url": "admin-shell:site-factory-orders"},
                    {"label": f"Projeto #{order.id}", "url": None},
                    {"label": "Producao", "url": None},
                ],
                "page_actions": [
                    {"label": "Ver Projeto", "href": reverse("admin-shell:site-factory-order-detail", kwargs={"pk": order.pk})},
                ],
                "tasks": order.production_tasks.select_related("assignee").order_by("order", "id"),
                "task_status_tones": TASK_STATUS_TONES,
            }
        )
        return context


class SiteFactoryTaskStatusView(SiteFactoryShellMixin, View):
    permission_domain = "dashboard"
    permission_action = "view"

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        task = get_object_or_404(order.production_tasks.all(), pk=kwargs["task_pk"])
        action = request.POST.get("action")
        if action == "start":
            ProductionService.mark_task_status(task=task, status=ProductionTask.Status.IN_PROGRESS)
            messages.success(request, "Tarefa iniciada.")
        elif action == "complete":
            if task.status != ProductionTask.Status.IN_PROGRESS:
                messages.error(request, "Inicie a tarefa antes de concluir.")
            else:
                ProductionService.mark_task_status(task=task, status=ProductionTask.Status.DONE)
                messages.success(request, "Tarefa concluida.")
        else:
            messages.error(request, "Acao de tarefa invalida.")
        return redirect("admin-shell:site-factory-order-tasks", pk=order.pk)
