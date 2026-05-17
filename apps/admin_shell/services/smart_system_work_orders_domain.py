"""Ordens de servico reais (Smart System) para o Admin Shell — queryset, escopo e serializacao."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.smart_system.models import (
    AssetHistoryEvent,
    FailureEvent,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
    WorkLog,
)
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def service_orders_base_queryset():
    return ServiceOrder.objects.select_related(
        "client",
        "client__company",
        "operational_site",
        "asset",
        "asset__category",
        "assigned_to",
        "created_by",
        "maintenance_plan",
        "maintenance_plan__checklist",
    ).order_by("-opened_at", "-id")


def scoped_service_orders(*, request=None, tenant_context=None):
    qs = service_orders_base_queryset()
    if request is not None:
        return SmartSystemScopeService.scope_queryset(qs, request)
    company = (tenant_context or {}).get("company")
    site = (tenant_context or {}).get("site")
    if company is not None:
        qs = qs.filter(client__company_id=company.id)
    if site is not None:
        qs = qs.filter(operational_site_id=site.id)
    return qs


def get_scoped_service_order(*, order_code: str, request=None, tenant_context=None) -> ServiceOrder | None:
    return scoped_service_orders(request=request, tenant_context=tenant_context).filter(order_number=order_code).first()


def _sla_fields(so: ServiceOrder) -> tuple[str, str]:
    now = timezone.now()
    deadline = so.scheduled_end or so.scheduled_start
    if so.status in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
        return "Sob controle", "—"
    if so.priority == ServiceOrder.Priority.URGENT:
        tone = "Critico"
    elif deadline and deadline < now:
        tone = "Critico"
    elif deadline and deadline < now + timedelta(hours=4):
        tone = "Em risco"
    else:
        tone = "Sob controle"
    deadline_display = deadline.strftime("%d/%m/%Y %H:%M") if deadline else "—"
    return tone, deadline_display


def _flow_key_for_status(status: str) -> str:
    return {
        ServiceOrder.Status.OPEN: "aberta",
        ServiceOrder.Status.SCHEDULED: "planejada",
        ServiceOrder.Status.IN_PROGRESS: "em_atendimento",
        ServiceOrder.Status.WAITING_QUOTE_APPROVAL: "aguardando_aprovacao",
        ServiceOrder.Status.WAITING_PARTS: "aguardando_peca",
        ServiceOrder.Status.ON_HOLD: "triagem",
        ServiceOrder.Status.COMPLETED: "concluida",
        ServiceOrder.Status.CANCELLED: "cancelada",
    }.get(status, "aberta")


def serialize_work_order_row(so: ServiceOrder) -> dict:
    asset = so.asset
    sla_status, sla_deadline = _sla_fields(so)
    asset_code = asset.asset_tag if asset else "—"
    asset_name = asset.name if asset else "—"
    return {
        "code": so.order_number,
        "title": so.title,
        "description": so.description or "",
        "maintenance_type": so.get_maintenance_type_display(),
        "maintenance_type_slug": so.maintenance_type,
        "origin": so.get_source_display(),
        "channel": "",
        "client": so.client.display_name,
        "site": so.operational_site.name,
        "sector": so.operational_site.name,
        "asset_code": asset_code,
        "asset_name": asset_name,
        "priority": so.get_priority_display(),
        "priority_slug": so.priority,
        "criticality": asset.get_criticality_display() if asset else so.get_priority_display(),
        "criticality_slug": asset.criticality if asset else "",
        "status": so.get_status_display(),
        "status_slug": so.status,
        "status_flow": _flow_key_for_status(so.status),
        "sla_status": sla_status,
        "sla_deadline": sla_deadline,
        "opened_at": so.opened_at.strftime("%d/%m/%Y %H:%M") if so.opened_at else "—",
        "due_at": so.scheduled_end.strftime("%d/%m/%Y %H:%M") if so.scheduled_end else "—",
        "started_at": so.started_at.strftime("%d/%m/%Y %H:%M") if so.started_at else "",
        "completed_at": so.completed_at.strftime("%d/%m/%Y %H:%M") if so.completed_at else "",
        "requester": so.requested_by or "—",
        "responsible": (so.assigned_to.get_full_name() or so.assigned_to.email) if so.assigned_to else "",
        "team": "",
        "estimated_hours": "",
        "executed_hours": "",
        "piece_required": so.status == ServiceOrder.Status.WAITING_PARTS,
        "piece_pending": so.status == ServiceOrder.Status.WAITING_PARTS,
        "has_recent_failure": False,
        "waiting_piece_days": 0,
        "has_checklist": bool(so.maintenance_plan and so.maintenance_plan.checklist_id),
        "opened_at_iso": so.opened_at.date().isoformat() if so.opened_at else "",
    }


def _diagnosis_from_order(so: ServiceOrder) -> dict:
    return {
        "apparent_cause": (so.description or "")[:400] or "—",
        "technical_diagnosis": (so.final_observations or "—")[:800],
        "action_taken": "—",
        "recommendation": so.notes[:400] if so.notes else "—",
        "return_needed": "Sim" if so.quote_required else "Nao",
        "materials": "—",
        "technical_notes": so.notes or "—",
    }


def _timeline_from_order(so: ServiceOrder, work_logs: list[WorkLog], history: list[AssetHistoryEvent]) -> list[dict]:
    items = []
    items.append(
        {
            "timestamp": so.opened_at.strftime("%d/%m/%Y %H:%M") if so.opened_at else "—",
            "actor": (so.created_by.get_full_name() or so.created_by.email) if so.created_by else "Sistema",
            "event_type": "OS aberta",
            "description": so.title,
            "reference": so.order_number,
            "timeline_tone": "info",
        }
    )
    for wl in work_logs:
        tech = (wl.user.get_full_name() or wl.user.email) if wl.user else "—"
        mins = wl.labor_minutes or 0
        h, m = divmod(mins, 60)
        duration_label = f"{h}h{m:02d} ({mins} min)" if mins else "0 min"
        items.append(
            {
                "timestamp": wl.started_at.strftime("%d/%m/%Y %H:%M"),
                "actor": tech,
                "event_type": "Apontamento de mao de obra",
                "description": wl.notes or f"Tempo registrado: {duration_label}.",
                "reference": f"WL-{wl.id}",
                "labor_minutes": mins,
                "duration_label": duration_label,
                "timeline_tone": "sky",
            }
        )
    for ev in history:
        items.append(
            {
                "timestamp": ev.occurred_at.strftime("%d/%m/%Y %H:%M"),
                "actor": (ev.created_by.get_full_name() or ev.created_by.email) if ev.created_by else "Sistema",
                "event_type": ev.get_event_type_display(),
                "description": ev.title + (f" — {ev.description}" if ev.description else ""),
                "reference": str(ev.public_id)[:8],
                "timeline_tone": "info",
            }
        )
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items


def serialize_work_order_detail(so: ServiceOrder, *, request=None) -> dict:
    row = serialize_work_order_row(so)
    asset = so.asset
    asset_payload = (
        {
            "code": asset.asset_tag,
            "name": asset.name,
            "category": asset.category.name if asset.category else "",
            "subcategory": "",
            "criticality": asset.get_criticality_display(),
            "operational_status": asset.get_status_display(),
            "history": [],
        }
        if asset
        else {"code": "—", "name": "—", "category": "", "subcategory": "", "criticality": row["criticality"], "operational_status": "—", "history": []}
    )

    work_logs = list(so.work_logs.select_related("user").order_by("-started_at")[:50])
    hist_q = Q(related_service_order=so)
    if asset:
        hist_q |= Q(asset=asset)
    history = list(
        AssetHistoryEvent.objects.filter(hist_q)
        .select_related("created_by", "asset")
        .order_by("-occurred_at")[:50]
    )

    failures = []
    if asset:
        for fe in FailureEvent.objects.filter(asset=asset).order_by("-detected_at")[:10]:
            failures.append(
                {
                    "code": str(fe.public_id)[:10].upper(),
                    "summary": (fe.symptom or "")[:120],
                    "status": fe.get_status_display(),
                    "detected_at": fe.detected_at.strftime("%d/%m/%Y %H:%M"),
                }
            )
    linked_movements = []
    for mv in StockMovement.objects.filter(service_order=so).select_related("part").order_by("-occurred_at")[:25]:
        linked_movements.append(
            {
                "part_code": mv.part.code,
                "part_name": mv.part.name,
                "type": mv.get_movement_type_display(),
                "quantity": str(mv.quantity),
                "at": mv.occurred_at.strftime("%d/%m/%Y %H:%M"),
            }
        )

    checklist_meta = None
    if so.maintenance_plan and so.maintenance_plan.checklist_id:
        cl = so.maintenance_plan.checklist
        checklist_meta = {"id": cl.id, "name": cl.name, "code": str(cl.public_id)[:8].upper()}

    quote = None
    from apps.smart_system.models import ServiceQuote

    q = ServiceQuote.objects.filter(work_order=so).order_by("-created_at").first()
    if q is not None:
        quote = {
            "quote_number": q.quote_number,
            "status": q.get_status_display(),
            "total_value": f"R$ {q.total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        }

    from django.urls import reverse

    order_code = so.order_number
    worklog_technician_options = []
    seen_u = set()
    if request and getattr(request, "user", None) and request.user.is_authenticated:
        worklog_technician_options.append(
            {
                "value": str(request.user.pk),
                "label": (request.user.get_full_name() or request.user.email or str(request.user.pk))[:120],
            }
        )
        seen_u.add(request.user.pk)
    if so.assigned_to_id and so.assigned_to_id not in seen_u:
        u = so.assigned_to
        worklog_technician_options.append({"value": str(u.pk), "label": (u.get_full_name() or u.email or str(u.pk))[:120]})

    page_actions = [
        {
            "label": "Execucao",
            "route_name": "admin-shell:smart-system-work-order-execution",
            "route_kwargs": {"order_code": order_code},
            "permission_domain": "work_execution",
            "permission_action": "execute",
        },
    ]
    if asset:
        page_actions.append(
            {
                "label": "Abrir ativo",
                "route_name": "admin-shell:smart-system-asset-detail",
                "route_kwargs": {"asset_code": asset.asset_tag},
                "permission_domain": "assets",
                "permission_action": "view",
            }
        )
    if quote:
        page_actions.insert(
            1,
            {
                "label": "Orcamento",
                "route_name": "admin-shell:smart-system-quote-detail",
                "route_kwargs": {"quote_number": quote["quote_number"]},
                "permission_domain": "quotes",
                "permission_action": "view",
            },
        )

    summary_cards = [
        {"label": "Status atual", "value": row["status"], "meta": "fluxo operacional"},
        {"label": "Prioridade", "value": row["priority"], "meta": "priorizacao"},
        {"label": "Criticidade", "value": row["criticality"], "meta": "ativo"},
        {"label": "SLA", "value": row["sla_status"], "meta": row["sla_deadline"]},
        {"label": "Responsavel", "value": row["responsible"] or "Sem responsavel", "meta": row["team"] or "—"},
        {"label": "Abertura", "value": row["opened_at"], "meta": "data de abertura"},
        {"label": "Prazo", "value": row["due_at"], "meta": "agendamento"},
    ]
    if quote:
        summary_cards.append({"label": "Orcamento", "value": quote["status"], "meta": f"{quote['quote_number']} • {quote['total_value']}"})

    transition_url = reverse("admin-shell:smart-system-work-order-transition", kwargs={"order_code": order_code})
    worklog_url = reverse("admin-shell:smart-system-work-order-worklog", kwargs={"order_code": order_code})

    action_panel = []
    if so.status not in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
        if so.status in (ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.ON_HOLD):
            action_panel.append(
                {
                    "label": "Iniciar atendimento",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "start"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                }
            )
        if so.status == ServiceOrder.Status.IN_PROGRESS:
            action_panel.append(
                {
                    "label": "Pausar (em espera)",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "pause"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                }
            )
        if so.status == ServiceOrder.Status.ON_HOLD:
            action_panel.append(
                {
                    "label": "Retomar",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "resume"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                }
            )
        if so.status == ServiceOrder.Status.WAITING_PARTS:
            action_panel.append(
                {
                    "label": "Pecas disponiveis — retomar",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "parts_ready"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                }
            )
        if so.status == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
            action_panel.append(
                {
                    "label": "Orcamento aprovado — continuar",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "quote_ready"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                }
            )
        action_panel.extend(
            [
                {
                    "label": "Registrar apontamento",
                    "method": "post",
                    "action_url": worklog_url,
                    "fields": [
                        {"name": "notes", "type": "textarea", "label": "Comentario", "required": True},
                        {"name": "hours", "type": "number", "label": "Horas", "step": "0.25", "required": False},
                    ]
                    + (
                        [
                            {
                                "name": "technician_id",
                                "type": "select",
                                "label": "Tecnico",
                                "required": False,
                                "options": worklog_technician_options,
                            }
                        ]
                        if worklog_technician_options
                        else []
                    ),
                    "permission_domain": "work_orders",
                    "permission_action": "update",
                },
                {
                    "label": "Cancelar OS",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "cancel"},
                    "permission_domain": "work_orders",
                    "permission_action": "update",
                },
            ]
        )
    action_panel.append(
        {
            "label": "Modo execucao",
            "route_name": "admin-shell:smart-system-work-order-execution",
            "route_kwargs": {"order_code": order_code},
            "permission_domain": "work_execution",
            "permission_action": "execute",
        }
    )
    if asset:
        action_panel.append(
            {
                "label": "Abrir ativo",
                "route_name": "admin-shell:smart-system-asset-detail",
                "route_kwargs": {"asset_code": asset.asset_tag},
                "permission_domain": "assets",
                "permission_action": "view",
            }
        )

    caller_info = [
        {"label": "Descricao", "value": so.description or "—"},
        {"label": "Origem", "value": so.get_source_display()},
        {"label": "Tipo", "value": so.get_maintenance_type_display()},
        {"label": "Solicitante", "value": so.requested_by or "—"},
        {"label": "Observacoes", "value": so.notes or "—"},
    ]
    context_info = [
        {"label": "Ativo", "value": asset_payload["name"]},
        {"label": "Tag / codigo", "value": asset_payload["code"]},
        {"label": "Categoria", "value": f"{asset_payload['category']} / {asset_payload['subcategory']}".strip(" /")},
        {"label": "Cliente", "value": row["client"]},
        {"label": "Site", "value": row["site"]},
        {"label": "Setor / localizacao", "value": row["sector"]},
        {"label": "Criticidade do ativo", "value": asset_payload["criticality"]},
        {"label": "Status do ativo", "value": asset_payload["operational_status"]},
    ]

    out = {
        **row,
        "status_slug": so.status,
        "code": so.order_number,
        "asset": asset_payload,
        "diagnosis": _diagnosis_from_order(so),
        "impact": "",
        "risk": "",
        "alerts": [],
        "timeline": _timeline_from_order(so, work_logs, history),
        "summary": {},
        "quote": quote,
        "page_actions": page_actions,
        "summary_cards": summary_cards,
        "status_flow_steps": build_status_flow_steps(_flow_key_for_status(so.status)),
        "caller_info": caller_info,
        "context_info": context_info,
        "sla_panel": {
            "deadline": row["sla_deadline"],
            "elapsed": "—",
            "risk": row["sla_status"],
            "priority": row["priority"],
            "criticality": row["criticality"],
            "impact": "",
            "traffic_light": "red" if row["sla_status"] == "Critico" else "amber" if row["sla_status"] == "Em risco" else "green",
        },
        "action_panel": action_panel,
        "work_logs": work_logs,
        "asset_history": history,
        "failures": failures,
        "stock_movements": linked_movements,
        "checklist_meta": checklist_meta,
        "service_order_id": so.id,
    }
    return out


def _response_label_safe(resp, item):
    from apps.smart_system.models import ChecklistItem

    if resp is None:
        return ""
    if item.item_type == ChecklistItem.ItemType.BOOLEAN:
        if resp.response_boolean is True:
            return "OK"
        if resp.response_boolean is False:
            return "NOK"
        return "N/A"
    if resp.response_text:
        return "OK"
    if resp.response_number is not None:
        return "OK"
    if resp.response_choice:
        return resp.response_choice
    return ""


def build_checklist_execution_for_order(so: ServiceOrder) -> tuple[dict | None, dict]:
    from apps.smart_system.models import ChecklistItem

    plan = so.maintenance_plan
    if not plan or not plan.checklist_id:
        return None, {
            "execution_code": "",
            "items": [],
            "total_items": 0,
            "responded_count": 0,
            "pending_count": 0,
            "ok_count": 0,
            "nok_count": 0,
            "na_count": 0,
            "progress": 0,
        }

    checklist = plan.checklist
    items = list(ChecklistItem.objects.filter(checklist=checklist, is_active=True).order_by("ordering", "id"))
    responses = {
        r.checklist_item_id: r
        for r in ServiceOrderChecklistResponse.objects.filter(service_order=so, checklist_item__checklist=checklist)
    }

    exec_items = []
    ok_c = nok_c = na_c = 0
    for it in items:
        resp = responses.get(it.id)
        label = _response_label_safe(resp, it)
        if label == "OK":
            ok_c += 1
        elif label == "NOK":
            nok_c += 1
        elif label == "N/A":
            na_c += 1
        exec_items.append(
            {
                "id": it.id,
                "order": it.ordering,
                "title": it.title,
                "description": it.description or "",
                "instruction": it.description or "",
                "response_type": "OK/NOK/N/A" if it.item_type == ChecklistItem.ItemType.BOOLEAN else it.get_item_type_display(),
                "required": it.is_required,
                "alert_on_nok": True,
                "default_note": "",
                "response": label,
                "note": (resp.notes if resp else "") or "",
                "response_text": (resp.response_text if resp else "") or "",
                "response_number": (resp.response_number if resp else None),
                "response_choice": (resp.response_choice if resp else "") or "",
                "timestamp": resp.updated_at.strftime("%d/%m/%Y %H:%M") if resp else "",
                "item_type": it.item_type,
            }
        )

    responded = sum(1 for x in exec_items if x["response"])
    total = len(exec_items)
    progress = int(round(100 * responded / total)) if total else 0

    checklist_dict = {
        "id": checklist.id,
        "code": str(checklist.public_id)[:12].upper(),
        "name": checklist.name,
        "preventive_plan_code": str(plan.public_id)[:12].upper() if plan else "",
    }
    execution_dict = {
        "execution_code": f"EX-{so.order_number}",
        "items": exec_items,
        "total_items": total,
        "responded_count": responded,
        "pending_count": max(total - responded, 0),
        "ok_count": ok_c,
        "nok_count": nok_c,
        "na_count": na_c,
        "progress": progress,
    }
    return checklist_dict, execution_dict


WORK_ORDER_STATUS_FLOW = [
    ("aberta", "Aberta"),
    ("triagem", "Triagem"),
    ("planejada", "Planejada"),
    ("atribuida", "Atribuida"),
    ("em_atendimento", "Em atendimento"),
    ("aguardando_peca", "Aguardando peca"),
    ("aguardando_aprovacao", "Aguardando aprovacao"),
    ("concluida", "Concluida"),
    ("cancelada", "Cancelada"),
]


def build_status_flow_steps(current_step: str) -> list[dict]:
    steps = []
    current_index = next((index for index, step in enumerate(WORK_ORDER_STATUS_FLOW) if step[0] == current_step), 0)
    for index, (key, label) in enumerate(WORK_ORDER_STATUS_FLOW):
        state = "done" if index < current_index else "current" if index == current_index else "upcoming"
        steps.append({"key": key, "label": label, "state": state})
    return steps


def log_status_change_event(so: ServiceOrder, user, previous_status: str, new_status: str) -> None:
    from apps.smart_system.services.maintenance_service import AssetHistoryService
    from apps.smart_system.models import AssetHistoryEvent

    if not so.asset or previous_status == new_status:
        return
    AssetHistoryService.create_event(
        asset=so.asset,
        event_type=AssetHistoryEvent.EventType.STATUS_CHANGED,
        title=f"OS {so.order_number}: status alterado",
        description=f"{previous_status} -> {new_status}",
        related_service_order=so,
        created_by=user,
    )
