"""Painel Administrativo Shell — Caneca de Garagem (visão inicial e pedidos)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Q, QuerySet, TextField
from django.db.models.functions import Cast
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.admin_shell.services.tenant_scope import build_shell_tenant_context
from apps.admin_shell.views import ShellContextMixin


class CanecaGaragemShellMixin(ShellContextMixin):
    """Mixin comum ao módulo Caneca no Admin Shell."""

    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = True
    current_module_slug = "caneca-de-garagem"

    def breadcrumb_tail_caneca(self):
        return [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Caneca de Garagem", "url": "admin-shell:caneca-dashboard"},
        ]

    def get_page_actions_orders(self):
        return [
            {
                "label": "Dashboard Caneca",
                "route_name": "admin-shell:caneca-dashboard",
                "permission_domain": "dashboard",
                "permission_action": "view",
            },
            {
                "label": "Lista de pedidos",
                "route_name": "admin-shell:caneca-order-list",
                "permission_domain": "dashboard",
                "permission_action": "view",
            },
        ]


def _caneca_order_signal_filter() -> Q:
    """Sinais de pedido relacionado à Caneca (metadata ou personalização ligada ao item)."""
    return (
        Q(items__customization_request__isnull=False)
        | Q(metadata__storefront="caneca_de_garagem")
        | Q(metadata__origin="caneca_de_garagem")
        | Q(metadata__source="caneca_de_garagem")
        | Q(metadata__channel="caneca_de_garagem")
    )


def caneca_marketplace_orders_queryset(request: HttpRequest) -> QuerySet:
    """
    queryset base MarketplaceOrder para a Caneca.
    - Escopo empresa ativa quando existir (mesmo critério do dashboard).
    - Se houver pedidos compatíveis com sinais caneca, limita a eles.
    - Caso contrário, devolve todos do escopo (fallback seguro, sem erro).
    """
    from apps.market_core.models import MarketplaceOrder

    qs = MarketplaceOrder.objects.all()
    tenant = build_shell_tenant_context(request)
    company = tenant.get("company")
    if company is not None:
        qs = qs.filter(company_id=company.id)

    narrowed = qs.filter(_caneca_order_signal_filter()).distinct()
    if narrowed.exists():
        return narrowed

    return qs.distinct()


def order_item_prefetch(with_customization: bool = True):
    """Prefetch consistente dos itens (produto/vendor + optional customization)."""
    from apps.market_core.models import MarketplaceOrderItem

    item_qs = MarketplaceOrderItem.objects.select_related("product", "product__vendor", "vendor").order_by(
        "id",
    )
    if with_customization:
        item_qs = item_qs.select_related("customization_request")
    return Prefetch("items", queryset=item_qs)


def get_caneca_dashboard_kpis(request) -> dict[str, Any]:
    """
    Agrega KPIs a partir dos models market_core / caneca_de_garagem.
    Em caso de model indisponível ou erro ORM, retorna zeros (sem propagar).
    """
    fallback = {
        "orders_total": 0,
        "orders_new": 0,
        "orders_attending": 0,
        "in_production": 0,
        "products_active": 0,
        "vendors_active": 0,
        "customization_pending": 0,
        "scopes_company": False,
    }
    try:
        from apps.caneca_de_garagem.models import CustomizationRequest, ProductionJob
        from apps.market_core.models import MarketplaceOrder, MarketplaceProduct, MarketplaceVendor

        tenant = build_shell_tenant_context(request)
        company = tenant.get("company")

        orders = MarketplaceOrder.objects.all()
        products = MarketplaceProduct.objects.all()
        vendors = MarketplaceVendor.objects.all()
        jobs = ProductionJob.objects.all()

        customization_qs = CustomizationRequest.objects.select_related(
            "order_item__order",
        )

        if company is not None:
            cid = company.id
            fallback["scopes_company"] = True
            orders = orders.filter(company_id=cid)
            products = products.filter(vendor__company_id=cid)
            vendors = vendors.filter(company_id=cid)
            jobs = jobs.filter(
                Q(order__company_id=cid)
                | Q(order_item__order__company_id=cid)
            )
            customization_qs = customization_qs.filter(order_item__order__company_id=cid)

        status = MarketplaceOrder.Status
        orders_cancelled_excluded = orders.exclude(status=status.CANCELLED)

        in_production_count = orders.filter(status=status.IN_PRODUCTION).count()
        prod_jobs_running = jobs.filter(
            status__in=[
                ProductionJob.Status.QUEUED,
                ProductionJob.Status.IN_PROGRESS,
            ]
        ).count()

        customization_pending = customization_qs.filter(
            approval_status=CustomizationRequest.ApprovalStatus.PENDING,
        ).count()

        fallback.update(
            {
                "orders_total": orders_cancelled_excluded.count(),
                "orders_new": orders.filter(status=status.PENDING).count(),
                "orders_attending": orders.filter(status=status.PAID).count(),
                "in_production": max(in_production_count, prod_jobs_running),
                "products_active": products.filter(is_active=True).count(),
                "vendors_active": vendors.filter(
                    status=MarketplaceVendor.Status.ACTIVE,
                ).count(),
                "customization_pending": customization_pending,
            }
        )
    except Exception:
        pass

    return fallback


def _metadata_contact(order) -> tuple[str, str]:
    md = order.metadata if isinstance(order.metadata, dict) else {}
    name = ""
    phone = ""
    for key in (
        "customer_name",
        "contact_name",
        "full_name",
        "name",
    ):
        v = md.get(key)
        if isinstance(v, str) and v.strip():
            name = v.strip()
            break
    for key in (
        "whatsapp",
        "whatsapp_phone",
        "customer_phone",
        "phone",
        "mobile",
        "telephone",
    ):
        v = md.get(key)
        if isinstance(v, str) and v.strip():
            phone = v.strip()
            break
    return name, phone


def _customer_display_parts(order) -> tuple[str, str, str]:
    """Cliente: nome para exibir, e-mail, telefone/metadata."""
    cust = getattr(order, "customer", None)
    email_guess = getattr(cust, "email", None) if cust is not None else None
    if not isinstance(email_guess, str) or not email_guess.strip():
        email_guess = ""
    md_name, md_phone = _metadata_contact(order)
    md = order.metadata if isinstance(order.metadata, dict) else {}
    email_meta = ""
    for k in ("customer_email", "contact_email", "email"):
        v = md.get(k)
        if isinstance(v, str) and v.strip():
            email_meta = v.strip()
            break
    name = ""
    if cust is not None:
        gf = getattr(cust, "get_full_name", None)
        combined = gf().strip() if callable(gf) else ""
        fname = getattr(cust, "first_name", "") or ""
        lname = getattr(cust, "last_name", "") or ""
        name = combined or (" ".join((fname, lname))).strip()
        name = name or getattr(cust, "username", "") or ""
    if not name and md_name:
        name = md_name.strip()
    if email_guess:
        email_disp = email_guess
    elif email_meta:
        email_disp = email_meta
    else:
        email_disp = ""
    phone_disp = (md_phone or "").strip()

    return name or "—", email_disp or "—", phone_disp or "—"


def _first_line_item(order) -> Any | None:
    items = getattr(order, "items", None)
    if items is None:
        return None
    first = getattr(items, "all", lambda: [])()
    if hasattr(first, "exists") and callable(first.exists):
        if not first.exists():
            return None
        return first.order_by("id").first()
    rl = list(first)
    rl.sort(key=lambda x: getattr(x, "id", 0))
    return rl[0] if rl else None


def _qty_total(order) -> int:
    """Soma quantities dos itens; fallback 0."""
    items = getattr(order, "items", None)
    if items is None:
        return 0
    qs = getattr(items, "all", lambda: [])()
    if hasattr(qs, "aggregate"):
        from django.db.models import Sum

        agg = qs.aggregate(s=Sum("quantity"))
        s = agg.get("s") or 0
        try:
            return int(s)
        except (TypeError, ValueError):
            return 0
    total = 0
    for row in qs:
        try:
            total += int(row.quantity or 0)
        except (TypeError, ValueError):
            pass
    return total


class CanecaGaragemDashboardView(CanecaGaragemShellMixin, TemplateView):
    """Dashboard inicial Caneca de Garagem dentro do Admin Shell."""

    template_name = "admin_shell/caneca_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kpi_raw = get_caneca_dashboard_kpis(self.request)

        pending_note = ""
        if kpi_raw["customization_pending"] and kpi_raw["scopes_company"]:
            pending_note = f"{kpi_raw['customization_pending']} personalizações em análise (pedido relacionado)"

        summary_cards = [
            {
                "label": "Pedidos / orçamentos (exc. cancelados)",
                "value": kpi_raw["orders_total"],
                "delta": "MarketplaceOrder",
                "tone": "amber",
            },
            {
                "label": "Pedidos novos",
                "value": kpi_raw["orders_new"],
                "delta": pending_note or "Status pendente no pedido",
                "tone": "indigo",
            },
            {
                "label": "Em atendimento",
                "value": kpi_raw["orders_attending"],
                "delta": "Pagos / fila até produção",
                "tone": "sky",
            },
            {
                "label": "Em produção",
                "value": kpi_raw["in_production"],
                "delta": "Pedidos em produção ou jobs na fila",
                "tone": "emerald",
            },
            {
                "label": "Produtos ativos",
                "value": kpi_raw["products_active"],
                "delta": "MarketplaceProduct",
                "tone": "orange",
            },
            {
                "label": "Criadores / parceiros ativos",
                "value": kpi_raw["vendors_active"],
                "delta": "MarketplaceVendor",
                "tone": "violet",
            },
        ]

        context["page_title"] = "Caneca de Garagem"
        context["page_description"] = (
            "Marketplace curado de personalizados, pedidos e produção sob demanda."
        )
        context["breadcrumbs"] = self.breadcrumb_tail_caneca()
        context["current_module_slug"] = self.current_module_slug
        context["summary_cards"] = summary_cards
        context["kpis_fallback_all_zero"] = all(
            card["value"] == 0 for card in summary_cards
        )
        context["page_actions"] = self.get_page_actions_orders()
        context["future_actions"] = [
            {
                "label": "Pedidos / Orçamentos",
                "soon": False,
                "route_name": "admin-shell:caneca-order-list",
            },
            {"label": "Produtos", "soon": True},
            {"label": "Criadores", "soon": True},
            {"label": "Produção", "soon": True},
        ]
        return context


class CanecaOrderListView(CanecaGaragemShellMixin, ListView):
    """Lista administrativa MarketplaceOrder para a Caneca."""

    template_name = "admin_shell/caneca_order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        from apps.market_core.models import MarketplaceOrder

        qs = (
            caneca_marketplace_orders_queryset(self.request)
            .select_related("customer", "company")
            .prefetch_related(order_item_prefetch(True))
            .order_by("-ordered_at", "-id")
        )

        st = (self.request.GET.get("status") or "").strip()
        allowed = [c for c, _lbl in MarketplaceOrder.Status.choices]
        if st in allowed:
            qs = qs.filter(status=st)

        df = parse_date(self.request.GET.get("date_from") or "")
        dt_end = parse_date(self.request.GET.get("date_to") or "")
        if df:
            qs = qs.filter(ordered_at__date__gte=df)
        if dt_end:
            qs = qs.filter(ordered_at__date__lte=dt_end)

        q = (self.request.GET.get("q") or "").strip()
        if q:
            sub = (
                Q(code__icontains=q)
                | Q(notes__icontains=q)
                | Q(items__product__name__icontains=q)
                | Q(items__product__slug__icontains=q)
                | Q(items__product__sku__icontains=q)
            )
            uq = (
                Q(customer__username__icontains=q)
                | Q(customer__email__icontains=q)
                | Q(customer__first_name__icontains=q)
                | Q(customer__last_name__icontains=q)
            )
            qs = (
                qs.annotate(metadata_txt=Cast("metadata", TextField()))
                .filter(sub | uq | Q(metadata_txt__icontains=q))
                .distinct()
            )

        return qs

    def _decorate_order_rows(self, orders_seq) -> None:
        """Anexa atributos apenas para templates (lista)."""
        for order in orders_seq:
            name, email, phone = _customer_display_parts(order)
            order.shell_display_customer_name = name
            order.shell_display_customer_email = email
            order.shell_display_customer_phone = phone
            fi = _first_line_item(order)
            order.shell_first_item = fi
            if fi is not None and getattr(fi, "product", None):
                order.shell_product_label = getattr(fi.product, "name", "") or "—"
            else:
                order.shell_product_label = "—"
            vend = getattr(fi, "vendor", None) if fi else None
            if vend is None and fi is not None and getattr(fi, "product", None):
                vend = getattr(fi.product, "vendor", None)
            order.shell_vendor_label = getattr(vend, "name", "") if vend else "—"
            qty = _qty_total(order)
            if qty:
                order.shell_qty_display = qty
            elif fi is not None:
                order.shell_qty_display = getattr(fi, "quantity", 0) or 0
            else:
                order.shell_qty_display = 0

    def get_context_data(self, **kwargs):
        from apps.market_core.models import MarketplaceOrder

        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Pedidos / orçamentos"
        ctx["page_description"] = (
            "MarketplaceOrder do escopo atual. Preferência por sinais Caneca (personalização ou metadata storefront/origin)."
        )
        crumbs = self.breadcrumb_tail_caneca()
        crumbs.append({"label": "Pedidos / Orçamentos", "url": None})
        ctx["breadcrumbs"] = crumbs
        ctx["page_actions"] = self.get_page_actions_orders()
        ctx["status_choices"] = MarketplaceOrder.Status.choices
        ctx["current_status"] = (self.request.GET.get("status") or "").strip()
        ctx["search_q"] = (self.request.GET.get("q") or "").strip()
        ctx["date_from"] = (self.request.GET.get("date_from") or "").strip()
        ctx["date_to"] = (self.request.GET.get("date_to") or "").strip()

        qp = ""
        preserve = dict(self.request.GET)
        preserve.pop("page", None)
        if preserve:
            qp = urlencode(preserve, doseq=True)
        ctx["pagination_query_prefix"] = qp

        page_obj = ctx.get("page_obj")
        if page_obj is not None:
            self._decorate_order_rows(page_obj.object_list)
        else:
            objs = ctx.get(self.context_object_name)
            if objs is not None:
                self._decorate_order_rows(objs)

        return ctx


class CanecaOrderDetailView(CanecaGaragemShellMixin, DetailView):
    """Detalhe de pedido MarketplaceOrder."""

    template_name = "admin_shell/caneca_order_detail.html"
    context_object_name = "order"
    pk_url_kwarg = "order_id"

    def get_queryset(self):
        from apps.caneca_de_garagem.models import ProductionJob

        return (
            caneca_marketplace_orders_queryset(self.request)
            .select_related("customer", "company")
            .prefetch_related(
                order_item_prefetch(True),
                Prefetch(
                    "production_jobs",
                    queryset=ProductionJob.objects.select_related(
                        "vendor",
                        "order_item",
                        "internal_factory",
                    ).order_by("id"),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        from apps.market_core.models import MarketplaceOrder

        ctx = super().get_context_data(**kwargs)
        order = ctx["order"]

        crumbs = self.breadcrumb_tail_caneca()
        crumbs.append({"label": "Pedidos / Orçamentos", "url": "admin-shell:caneca-order-list"})
        crumbs.append({"label": order.code, "url": None})
        ctx["breadcrumbs"] = crumbs

        name, email, phone = _customer_display_parts(order)
        ctx["display_customer_name"] = name
        ctx["display_customer_email"] = email
        ctx["display_customer_phone"] = phone

        try:
            ctx["metadata_pretty"] = json.dumps(order.metadata or {}, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            ctx["metadata_pretty"] = "—"

        ctx["production_jobs"] = list(order.production_jobs.all()) if hasattr(order, "production_jobs") else []
        try:
            shipment = order.shipment_preparation
        except ObjectDoesNotExist:
            shipment = None
        ctx["shipment_preparation"] = shipment

        ctx["qty_total"] = _qty_total(order)

        customization_rows = []
        for it in order.items.all():
            cust_req = getattr(it, "customization_request", None)
            cust_text_pretty = "—"
            if cust_req is not None and cust_req.customer_text:
                try:
                    cust_text_pretty = json.dumps(cust_req.customer_text, indent=2, ensure_ascii=False)
                except (TypeError, ValueError):
                    cust_text_pretty = "—"
            customization_rows.append(
                {
                    "item": it,
                    "customization_request": cust_req,
                    "customer_text_pretty": cust_text_pretty,
                }
            )
        ctx["line_items_detail"] = customization_rows

        ctx["order_status_choices"] = list(MarketplaceOrder.Status.choices)
        ctx["page_actions"] = self.get_page_actions_orders()
        ctx["page_description"] = f"Pedido {order.code} · status atual {order.get_status_display()}"
        ctx["page_title"] = f"Pedido {order.code}"
        ctx["status_update_url"] = reverse("admin-shell:caneca-order-status", kwargs={"order_id": order.pk})
        return ctx


class CanecaOrderStatusView(CanecaGaragemShellMixin, View):
    """POST apenas: altera MarketplaceOrder.status com choices válidas."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, order_id: int) -> HttpResponse:
        from apps.market_core.models import MarketplaceOrder

        qs = caneca_marketplace_orders_queryset(request)
        order = get_object_or_404(qs, pk=order_id)
        raw = (request.POST.get("status") or "").strip()

        labels = dict(MarketplaceOrder.Status.choices)
        if raw not in labels:
            messages.warning(request, "Status não reconhecido. Nenhuma alteração foi gravada.")
            return redirect(reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk}))

        prev = order.status
        order.status = raw
        order.save(update_fields=["status", "updated_at"])

        if prev != raw:
            messages.success(
                request,
                f'Status atualizado de "{labels.get(prev, prev)}" para "{labels.get(raw, raw)}".',
            )
        else:
            messages.success(request, "Status mantido.")

        return redirect(reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk}))

