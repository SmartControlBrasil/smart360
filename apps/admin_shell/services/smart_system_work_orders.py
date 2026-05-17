"""Ordens de servico no Admin Shell — dados reais (ORM) e listagem."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q

from apps.smart_system.models import ServiceOrder

from .smart_system_work_orders_domain import (
    WORK_ORDER_STATUS_FLOW,
    get_scoped_service_order,
    scoped_service_orders,
    serialize_work_order_detail,
    serialize_work_order_row,
)

def _normalize(value):
    return (value or "").strip().lower()


def get_work_order_options(*, request=None, tenant_context=None):
    qs = scoped_service_orders(request=request, tenant_context=tenant_context)
    return {
        "clients": [],
        "sites": [],
        "types": [label for value, label in ServiceOrder.MaintenanceType.choices],
        "type_values": [value for value, _label in ServiceOrder.MaintenanceType.choices],
        "statuses": [label for value, label in ServiceOrder.Status.choices],
        "status_values": [value for value, _label in ServiceOrder.Status.choices],
        "priorities": [label for value, label in ServiceOrder.Priority.choices],
        "priority_values": [value for value, _label in ServiceOrder.Priority.choices],
        "technicians": [],
        "technician_values": [],
        "periods": [],
    }


def _apply_list_filters(qs, filters):
    search = _normalize(filters.get("search"))
    if search:
        qs = qs.filter(
            Q(order_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(asset__asset_tag__icontains=search)
            | Q(asset__name__icontains=search)
        )
    status_slug = filters.get("status") or filters.get("status_slug")
    if status_slug:
        qs = qs.filter(status=status_slug)
    mtype = filters.get("maintenance_type") or filters.get("type")
    if mtype:
        qs = qs.filter(maintenance_type=mtype)
    priority = filters.get("priority")
    if priority:
        qs = qs.filter(priority=priority)
    tech = filters.get("technician") or filters.get("assigned_to")
    if tech:
        try:
            qs = qs.filter(assigned_to_id=int(tech))
        except (TypeError, ValueError):
            pass
    piece_pending = _normalize(filters.get("piece_pending"))
    if piece_pending in ("yes", "true", "1", "sim"):
        qs = qs.filter(status=ServiceOrder.Status.WAITING_PARTS)
    return qs


def _filter_options_for_queryset(qs):
    tech_ids = list(qs.exclude(assigned_to__isnull=True).values_list("assigned_to_id", "assigned_to__email").distinct()[:50])
    technicians = []
    technician_values = []
    for uid, email in qs.exclude(assigned_to__isnull=True).values_list("assigned_to_id", "assigned_to__email").distinct():
        if uid:
            technician_values.append(str(uid))
            technicians.append(email or f"user-{uid}")
    return technicians, technician_values


def _build_filters(filters, request=None, tenant_context=None):
    qs = scoped_service_orders(request=request, tenant_context=tenant_context)
    technicians, technician_values = _filter_options_for_queryset(qs)
    return [
        {"label": "Buscar OS / ativo", "name": "search", "type": "search", "value": filters.get("search", ""), "placeholder": "Codigo, titulo ou ativo"},
        {
            "label": "Status",
            "name": "status",
            "type": "select",
            "value": filters.get("status", ""),
            "options": [{"value": v, "label": lbl} for v, lbl in ServiceOrder.Status.choices],
        },
        {
            "label": "Tipo de manutencao",
            "name": "maintenance_type",
            "type": "select",
            "value": filters.get("maintenance_type", ""),
            "options": [{"value": v, "label": lbl} for v, lbl in ServiceOrder.MaintenanceType.choices],
        },
        {
            "label": "Prioridade",
            "name": "priority",
            "type": "select",
            "value": filters.get("priority", ""),
            "options": [{"value": v, "label": lbl} for v, lbl in ServiceOrder.Priority.choices],
        },
        {
            "label": "Tecnico (responsavel)",
            "name": "technician",
            "type": "select",
            "value": filters.get("technician", ""),
            "options": [{"value": tid, "label": tname} for tid, tname in zip(technician_values, technicians)],
        },
    ]


def get_work_order_listing_context(request, filters=None, tenant_context=None, per_page=25):
    filters = filters or {}
    base = scoped_service_orders(request=request, tenant_context=tenant_context)
    filtered = _apply_list_filters(base, filters)
    paginator = Paginator(filtered, per_page)
    page_number = int(request.GET.get("page", 1)) if request else 1
    page_obj = paginator.get_page(page_number)
    rows = [serialize_work_order_row(so) for so in page_obj.object_list]

    pagination_query = ""
    if request:
        qdict = request.GET.copy()
        qdict.pop("page", None)
        pagination_query = urlencode(qdict)

    open_q = ~Q(status__in=[ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED])
    open_count = base.filter(open_q).count()
    in_prog = base.filter(status=ServiceOrder.Status.IN_PROGRESS).count()
    completed_recent = base.filter(status=ServiceOrder.Status.COMPLETED).count()
    urgent_open = base.filter(open_q, priority=ServiceOrder.Priority.URGENT).count()
    waiting_parts = base.filter(status=ServiceOrder.Status.WAITING_PARTS).count()

    return {
        "page_actions": [
            {
                "label": "Nova OS corretiva",
                "route_name": "admin-shell:smart-system-work-order-create",
                "permission_domain": "work_orders",
                "permission_action": "create",
            },
            {
                "label": "Nova OS preventiva",
                "route_name": "admin-shell:smart-system-work-order-create-preventive",
                "permission_domain": "work_orders",
                "permission_action": "create",
            },
        ],
        "work_order_filters": _build_filters(filters, request=request, tenant_context=tenant_context),
        "work_order_kpis": [
            {"label": "Total (escopo)", "value": str(base.count()), "context": "ordens visiveis", "tone": "indigo"},
            {"label": "Em aberto", "value": str(open_count), "context": "nao concluidas nem canceladas", "tone": "sky"},
            {"label": "Em andamento", "value": str(in_prog), "context": "status em progresso", "tone": "teal"},
            {"label": "Urgentes abertas", "value": str(urgent_open), "context": "prioridade urgente", "tone": "red"},
            {"label": "Aguardando pecas", "value": str(waiting_parts), "context": "status aguardando pecas", "tone": "amber"},
            {"label": "Concluidas (carteira)", "value": str(completed_recent), "context": "no escopo atual", "tone": "emerald"},
        ],
        "work_orders": rows,
        "work_order_page": page_obj,
        "work_order_paginator": paginator,
        "work_order_pagination_query": pagination_query,
        "work_order_operational_note": {
            "title": "Ordens de servico",
            "subtitle": "Listagem a partir do modelo ServiceOrder com escopo de tenant e filtros reais.",
        },
    }


def get_work_order_by_code(order_code, request=None, tenant_context=None):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=tenant_context)
    if so is None:
        return None
    return serialize_work_order_row(so)


def get_work_order_detail_context(order_code, request=None, tenant_context=None):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=tenant_context)
    if so is None:
        return None
    return serialize_work_order_detail(so, request=request)
