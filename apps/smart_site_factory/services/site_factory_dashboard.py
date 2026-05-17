"""Contexto agregado para o dashboard operacional HTML do Smart Site Factory."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from django.db.models import Count, Sum

from ..models import DeliveryRecord, Niche, ProductionTask, SiteOrder, Template
from .template_package import order_package_chart_label


def apply_dashboard_filters(queryset, *, get_params):
    """Aplica filtros GET comuns ao dashboard e à listagem de pedidos."""
    status = get_params.get("status") or ""
    if status:
        queryset = queryset.filter(status=status)
    lifecycle = get_params.get("lifecycle") or ""
    if lifecycle == "active":
        queryset = queryset.exclude(
            status__in=[SiteOrder.Status.DELIVERED, SiteOrder.Status.CANCELLED],
        )
    if get_params.get("briefing") == "pending":
        queryset = queryset.filter(status=SiteOrder.Status.INTAKE_PENDING, intake__isnull=True)
    niche_id = get_params.get("niche") or ""
    if niche_id.isdigit():
        queryset = queryset.filter(niche_id=int(niche_id))
    template_id = get_params.get("template") or ""
    if template_id.isdigit():
        queryset = queryset.filter(selected_template_id=int(template_id))
    return queryset


def build_kpis(queryset):
    """KPIs sobre o queryset já escopado por tenant (e opcionalmente filtrado)."""
    active = queryset.exclude(
        status__in=[SiteOrder.Status.DELIVERED, SiteOrder.Status.CANCELLED],
    ).count()
    awaiting_briefing = queryset.filter(
        status=SiteOrder.Status.INTAKE_PENDING,
        intake__isnull=True,
    ).count()
    in_production = queryset.filter(status=SiteOrder.Status.IN_PRODUCTION).count()
    delivered = queryset.filter(status=SiteOrder.Status.DELIVERED).count()
    potential = (
        queryset.exclude(status__in=[SiteOrder.Status.DELIVERED, SiteOrder.Status.CANCELLED]).aggregate(
            total=Sum("final_price"),
        )["total"]
        or Decimal("0")
    )
    order_ids = list(queryset.values_list("id", flat=True))
    pending_tasks = 0
    if order_ids:
        pending_tasks = ProductionTask.objects.filter(
            site_order_id__in=order_ids,
            status__in=[
                ProductionTask.Status.TODO,
                ProductionTask.Status.IN_PROGRESS,
                ProductionTask.Status.BLOCKED,
            ],
        ).count()
    return {
        "active_projects": active,
        "awaiting_briefing": awaiting_briefing,
        "in_production": in_production,
        "delivered": delivered,
        "potential_revenue": potential,
        "pending_tasks": pending_tasks,
    }


def orders_by_status_series(queryset):
    rows = (
        queryset.values("status")
        .annotate(c=Count("id"))
        .order_by("-c")
    )
    labels = []
    values = []
    status_labels = dict(SiteOrder.Status.choices)
    for row in rows:
        labels.append(status_labels.get(row["status"], row["status"]))
        values.append(row["c"])
    return {"labels": labels, "series": values}


def top_niches_series(queryset, *, limit=8):
    rows = (
        queryset.values("niche__name")
        .annotate(c=Count("id"))
        .order_by("-c")[:limit]
    )
    return {
        "labels": [r["niche__name"] or "-" for r in rows],
        "series": [r["c"] for r in rows],
    }


def top_commercial_packages_series(queryset, *, limit=8):
    """Agrupa pedidos por pacote (snapshot ou metadata do template), em Python."""
    rows = list(queryset.select_related("selected_template"))
    counts: Counter[str] = Counter()
    for order in rows:
        counts[order_package_chart_label(order)] += 1
    top = counts.most_common(limit)
    return {"labels": [pair[0] for pair in top], "series": [pair[1] for pair in top]}


def recent_orders(queryset, *, limit=8):
    return list(queryset.order_by("-ordered_at")[:limit])


def recent_deliveries(scoped_order_ids, *, limit=8):
    if not scoped_order_ids:
        return []
    return list(
        DeliveryRecord.objects.filter(site_order_id__in=scoped_order_ids)
        .select_related("site_order", "site_order__company", "site_order__niche")
        .order_by("-delivered_at")[:limit]
    )


def pending_tasks_detail(scoped_order_ids, *, limit=12):
    if not scoped_order_ids:
        return []
    return list(
        ProductionTask.objects.filter(
            site_order_id__in=scoped_order_ids,
            status__in=[
                ProductionTask.Status.TODO,
                ProductionTask.Status.IN_PROGRESS,
                ProductionTask.Status.BLOCKED,
            ],
        )
        .select_related("site_order", "assignee")
        .order_by("site_order_id", "order", "id")[:limit]
    )


def filter_option_querysets():
    return {
        "niches": Niche.objects.filter(is_active=True).order_by("name"),
        "templates": Template.objects.filter(is_active=True, status=Template.Status.READY)
        .select_related("niche")
        .order_by("niche__name", "name"),
    }
