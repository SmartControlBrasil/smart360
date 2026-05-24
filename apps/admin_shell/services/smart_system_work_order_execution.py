"""Contexto de execucao de OS — dados reais (ServiceOrder, checklist, work logs, assinaturas)."""

from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

from apps.smart_system.models import FailureEvent, FieldExecutionSnapshot, ServiceOrder
from apps.smart_system.services.offline_sync import FieldOfflineSyncService
from apps.smart_system.services.signature_service import ServiceSignatureService

from .smart_system_work_orders_domain import (
    build_checklist_execution_for_order,
    get_scoped_service_order,
    safe_user_display_name,
)


def _blank_checklist_context():
    return {
        "checklist": None,
        "execution": {
            "execution_code": "",
            "items": [],
            "total_items": 0,
            "responded_count": 0,
            "pending_count": 0,
            "ok_count": 0,
            "nok_count": 0,
            "na_count": 0,
            "progress": 0,
        },
    }


def _work_logs_as_hours(so: ServiceOrder) -> list[dict]:
    rows = []
    for wl in so.work_logs.select_related("user").order_by("-started_at")[:30]:
        tech = safe_user_display_name(wl.user) if wl.user else "—"
        mins = wl.labor_minutes or 0
        h, m = divmod(mins, 60)
        rows.append(
            {
                "technician": tech,
                "started_at": wl.started_at.strftime("%d/%m/%Y %H:%M"),
                "finished_at": wl.ended_at.strftime("%d/%m/%Y %H:%M") if wl.ended_at else "",
                "duration": f"{h}h{m:02d}",
                "labor_minutes": mins,
                "minutes_label": f"{mins} min" if mins else "0 min",
                "description": wl.notes or "",
            }
        )
    return rows


def _sum_hours(hours):
    total_minutes = 0
    for hour in hours:
        duration = hour.get("duration", "0h00")
        try:
            hours_part, minutes_part = duration.split("h", 1)
            total_minutes += int(hours_part) * 60 + int(minutes_part or "0")
        except (ValueError, IndexError):
            pass
    return f"{total_minutes // 60}h{total_minutes % 60:02d}"


def _merge_offline_snapshot(execution, snapshot):
    checklist_payload = snapshot.checklist_payload or {}
    diagnosis_payload = snapshot.diagnosis_payload or {}
    action_payload = snapshot.executed_action_payload or {}
    materials_payload = snapshot.materials_payload or []
    evidence_payload = snapshot.evidence_payload or []
    finalization_payload = snapshot.finalization_payload or {}

    if checklist_payload and isinstance(checklist_payload, dict) and checklist_payload.get("items"):
        execution["checklist_execution"] = {**execution["checklist_execution"], **checklist_payload}
    if diagnosis_payload:
        execution["diagnosis"] = {**execution["diagnosis"], **diagnosis_payload}
    if action_payload:
        execution["executed_action"] = {**execution["executed_action"], **action_payload}
    if materials_payload:
        execution["materials"] = materials_payload
    if evidence_payload:
        execution["evidence"] = evidence_payload
    if finalization_payload:
        execution["finalization"] = {**execution["finalization"], **finalization_payload}
    if snapshot.execution_status:
        execution["status"] = snapshot.execution_status
    if snapshot.progress:
        execution["progress"] = snapshot.progress
    if snapshot.started_at:
        execution["started_at"] = snapshot.started_at.strftime("%d/%m/%Y %H:%M")
    if snapshot.completed_at:
        execution["finished_at"] = snapshot.completed_at.strftime("%d/%m/%Y %H:%M")

    execution["offline_sync"] = FieldOfflineSyncService._serialize_snapshot(snapshot)
    if snapshot.sync_state == FieldExecutionSnapshot.SyncState.CONFLICT:
        execution["alerts"].append(
            {
                "severity": "critical",
                "title": "Conflito de sincronizacao detectado",
                "description": snapshot.last_conflict_message or "Ha dados locais que exigem revisao antes de nova sincronizacao.",
            }
        )


def _build_execution_alerts(order: dict, execution: dict, *, status_slug: str):
    alerts = []
    if status_slug == ServiceOrder.Status.WAITING_PARTS:
        alerts.append(
            {
                "severity": "warning",
                "title": "Aguardando pecas",
                "description": "A execucao esta pausada ate chegada ou liberacao de pecas. Use a acao "
                "\"Pecas disponiveis\" quando puder retomar o trabalho em campo.",
            }
        )
    elif status_slug == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
        alerts.append(
            {
                "severity": "warning",
                "title": "Aguardando aprovacao de orcamento",
                "description": "Retome somente apos aprovacao comercial. Use a acao \"Orcamento aprovado\" "
                "quando o cliente liberar a continuacao.",
            }
        )
    if not execution["checklist"]:
        alerts.append(
            {
                "severity": "warning",
                "title": "OS sem checklist vinculado",
                "description": "Associe um checklist ao plano de manutencao ou registre itens manualmente.",
            }
        )
    if status_slug not in (
        ServiceOrder.Status.WAITING_PARTS,
        ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
        ServiceOrder.Status.COMPLETED,
        ServiceOrder.Status.CANCELLED,
    ):
        if not execution["diagnosis"].get("technical_diagnosis") or execution["diagnosis"].get("technical_diagnosis") == "—":
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Diagnostico / observacoes finais",
                    "description": "Ao encerrar, preencha observacoes finais com o resultado do atendimento.",
                }
            )
    if execution["checklist_execution"].get("nok_count", 0):
        alerts.append(
            {
                "severity": "critical",
                "title": "Checklist com itens NOK",
                "description": f"{execution['checklist_execution']['nok_count']} item(ns) com anomalia.",
            }
        )
    if order.get("has_recent_failure"):
        alerts.append(
            {
                "severity": "warning",
                "title": "Ativo com falhas registradas",
                "description": "Consulte falhas vinculadas ao ativo.",
            }
        )
    if not execution["signatures"]["has_technician_signature"]:
        alerts.append(
            {
                "severity": "info",
                "title": "Assinatura do tecnico",
                "description": "Opcional para conclusao; recomendada para auditoria.",
            }
        )
    if not execution["signatures"]["has_client_resolution"]:
        alerts.append(
            {
                "severity": "info",
                "title": "Aceite do cliente",
                "description": "Opcional para conclusao; use justificativa se ausente.",
            }
        )
    return alerts


def get_work_order_execution_context(order_code, *, request=None, tenant_context=None):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=tenant_context)
    if so is None:
        return None

    from .smart_system_work_orders import get_work_order_detail_context

    order = get_work_order_detail_context(order_code, request=request, tenant_context=tenant_context)
    if order is None:
        return None

    asset = order.get("asset") or {"code": "", "name": ""}
    checklist, checklist_execution = build_checklist_execution_for_order(so)
    if checklist is None:
        checklist_ctx = _blank_checklist_context()
        checklist = checklist_ctx["checklist"]
        checklist_execution = checklist_ctx["execution"]

    hours = _work_logs_as_hours(so)
    diagnosis = {
        "symptoms": (so.description or "")[:500],
        "technical_diagnosis": (so.final_observations or "")[:800] or "—",
        "components": asset.get("name", "") or "",
        "analysis": so.notes or "",
        "operational_notes": (so.notes or "")[:2000] or "",
    }
    executed_action = {
        "intervention": "",
        "components_replaced": "",
        "adjustments": "",
        "tests": "",
        "result": so.get_status_display(),
    }
    finalization = {
        "final_status": so.get_status_display(),
        "final_diagnosis": so.final_observations or "",
        "final_action": "",
        "recommendation": "",
        "return_needed": "",
        "final_notes": so.notes or "",
        "final_observations": so.final_observations or "",
    }

    service_order = ServiceSignatureService.get_service_order(order_code)
    signature_summary = ServiceSignatureService.get_signature_summary(service_order) if service_order else {}

    snapshot = None
    if service_order is not None:
        snapshot = (
            FieldExecutionSnapshot.objects.filter(service_order=service_order)
            .select_related("technician")
            .order_by("-updated_at")
            .first()
        )

    started_display = so.started_at.strftime("%d/%m/%Y %H:%M") if so.started_at else "Aguardando inicio"
    finished_display = so.completed_at.strftime("%d/%m/%Y %H:%M") if so.completed_at else ""

    if so.status == ServiceOrder.Status.COMPLETED:
        progress = 100
    else:
        progress = checklist_execution.get("progress") or 0
        if so.status == ServiceOrder.Status.IN_PROGRESS and progress < 15:
            progress = 15

    executor = order.get("responsible") or "Nao atribuido"

    preventive_plan = None
    if so.maintenance_plan_id:
        mp = so.maintenance_plan
        preventive_plan = {
            "code": str(mp.public_id)[:12].upper(),
            "name": mp.name,
            "last_execution": mp.last_generated_at.strftime("%d/%m/%Y %H:%M") if mp.last_generated_at else "—",
        }

    recent_failures = []
    if so.asset_id:
        for fe in FailureEvent.objects.filter(asset_id=so.asset_id).order_by("-detected_at")[:5]:
            recent_failures.append(
                {
                    "code": str(fe.public_id)[:10].upper(),
                    "summary": (fe.symptom or "")[:120],
                    "date": fe.detected_at.strftime("%d/%m %H:%M"),
                }
            )

    transition_url = reverse("admin-shell:smart-system-work-order-transition", kwargs={"order_code": so.order_number})
    save_notes_url = reverse("admin-shell:smart-system-work-order-save-progress", kwargs={"order_code": so.order_number})
    checklist_url = reverse("admin-shell:smart-system-work-order-checklist-save", kwargs={"order_code": so.order_number})
    complete_url = reverse("admin-shell:smart-system-work-order-complete-execution", kwargs={"order_code": so.order_number})
    worklog_url = reverse("admin-shell:smart-system-work-order-worklog", kwargs={"order_code": so.order_number})

    worklog_technicians = []
    seen_ids = set()
    if request and request.user.is_authenticated:
        uid = request.user.pk
        seen_ids.add(uid)
        worklog_technicians.append(
            {"id": str(uid), "label": (safe_user_display_name(request.user) or str(uid))[:120]}
        )
    if so.assigned_to_id and so.assigned_to_id not in seen_ids:
        u = so.assigned_to
        worklog_technicians.append({"id": str(u.pk), "label": (safe_user_display_name(u) or str(u.pk))[:120]})

    execution = {
        "execution_code": f"EX-{so.order_number}",
        "order_code": so.order_number,
        "status_slug": so.status,
        "executor": executor,
        "status": so.get_status_display(),
        "started_at": started_display,
        "finished_at": finished_display,
        "progress": progress,
        "hours": hours,
        "worklog_url": worklog_url,
        "worklog_technicians": worklog_technicians,
        "materials": [],
        "evidence": [],
        "diagnosis": diagnosis,
        "executed_action": executed_action,
        "finalization": finalization,
        "timeline": order.get("timeline", []),
        "checklist": checklist,
        "checklist_execution": checklist_execution,
        "preventive_plan": preventive_plan,
        "signatures": signature_summary,
        "alerts": [],
    }

    if snapshot is not None:
        _merge_offline_snapshot(execution, snapshot)

    order["has_recent_failure"] = bool(recent_failures)

    execution["hours_total"] = _sum_hours(execution["hours"])
    execution["recent_asset_history"] = []
    execution["recent_failures"] = recent_failures
    execution["recent_preventives"] = (
        [{"code": preventive_plan["code"], "name": preventive_plan["name"], "date": preventive_plan["last_execution"]}]
        if preventive_plan
        else []
    )
    execution["alerts"] = _build_execution_alerts(order, execution, status_slug=so.status)
    ce = execution["checklist_execution"]
    cl_meta = execution["checklist"]["name"] if execution["checklist"] else "Sem checklist"
    if ce.get("total_items"):
        cl_meta = f"{ce['responded_count']}/{ce['total_items']} itens • {ce['pending_count']} pendente(s) • {cl_meta}"
    execution["progress_cards"] = [
        {"label": "Execucao", "value": f"{execution['progress']}%", "meta": execution["status"]},
        {
            "label": "Checklist",
            "value": f"{execution['checklist_execution'].get('progress', 0)}%",
            "meta": cl_meta,
        },
        {"label": "Horas registradas", "value": execution["hours_total"], "meta": f"{len(execution['hours'])} lancamento(s)"},
        {"label": "Materiais", "value": str(len(execution["materials"])), "meta": "pecas e insumos"},
        {
            "label": "Assinaturas",
            "value": f"{int(execution['signatures'].get('has_technician_signature', False)) + int(execution['signatures'].get('has_client_signature', False))}/2",
            "meta": "formalizacao",
        },
    ]
    execution["summary_cards"] = [
        {"label": "Tecnico", "value": execution["executor"], "meta": order.get("team") or "—"},
        {"label": "Inicio", "value": execution["started_at"], "meta": order.get("opened_at", "")},
        {"label": "Fim", "value": execution["finished_at"] or "Em aberto", "meta": order.get("due_at", "")},
        {"label": "Resultado", "value": execution["finalization"].get("final_status", execution["status"]), "meta": ""},
        {
            "label": "Aceite do cliente",
            "value": "Assinado"
            if execution["signatures"].get("has_client_signature")
            else ("Justificado" if execution["signatures"].get("missing_reason_recorded") else "Pendente"),
            "meta": "cliente ou representante",
        },
    ]
    tech_sig = execution["signatures"].get("technician_signature")
    client_sig = execution["signatures"].get("client_signature")
    execution["signature_cards"] = [
        {
            "label": "Assinatura do tecnico",
            "status": "Registrada" if execution["signatures"].get("has_technician_signature") else "Pendente",
            "meta": tech_sig.signed_at.strftime("%d/%m/%Y %H:%M") if tech_sig else "opcional",
            "signature": tech_sig,
        },
        {
            "label": "Aceite do cliente",
            "status": "Registrado"
            if execution["signatures"].get("has_client_signature")
            else ("Ausencia justificada" if execution["signatures"].get("missing_reason_recorded") else "Pendente"),
            "meta": client_sig.signed_at.strftime("%d/%m/%Y %H:%M") if client_sig else "opcional",
            "signature": client_sig,
        },
    ]

    page_actions = [
        {
            "label": "Relatorio tecnico",
            "href": f"/app/smart-system/reports/work-order/{order['code']}/",
            "permission_domain": "reports",
            "permission_action": "view",
        },
        {
            "label": "Baixar PDF",
            "href": f"/app/smart-system/reports/work-order/{order['code']}/download/",
            "permission_domain": "reports",
            "permission_action": "export",
        },
    ]
    if asset.get("code"):
        page_actions.append(
            {
                "label": "Abrir ativo",
                "route_name": "admin-shell:smart-system-asset-detail",
                "route_kwargs": {"asset_code": asset["code"]},
                "permission_domain": "assets",
                "permission_action": "view",
            }
        )

    readonly = so.status in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED)
    if not readonly:
        insert_at = 0
        if so.status == ServiceOrder.Status.WAITING_PARTS:
            page_actions.insert(
                insert_at,
                {
                    "label": "Pecas disponiveis — retomar execucao",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "parts_ready"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                },
            )
            insert_at += 1
        elif so.status == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
            page_actions.insert(
                insert_at,
                {
                    "label": "Orcamento aprovado — continuar",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "quote_ready"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                },
            )
            insert_at += 1
        if so.status == ServiceOrder.Status.IN_PROGRESS:
            page_actions.insert(
                insert_at,
                {
                    "label": "Pausar execucao",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "pause"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                },
            )
            insert_at += 1
        if so.status in (ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.ON_HOLD):
            page_actions.insert(
                insert_at,
                {
                    "label": "Iniciar execucao",
                    "method": "post",
                    "action_url": transition_url,
                    "hidden": {"transition": "start"},
                    "permission_domain": "work_execution",
                    "permission_action": "execute",
                },
            )
            insert_at += 1
        page_actions.insert(
            insert_at,
            {
                "label": "Salvar andamento (notas)",
                "method": "post",
                "action_url": save_notes_url,
                "fields": [{"name": "progress_notes", "type": "textarea", "label": "Notas de andamento", "required": False}],
                "permission_domain": "work_execution",
                "permission_action": "execute",
            },
        )
        insert_at += 1
        if so.status not in (ServiceOrder.Status.WAITING_PARTS, ServiceOrder.Status.WAITING_QUOTE_APPROVAL):
            page_actions.insert(
                insert_at,
                {
                    "label": "Concluir OS",
                    "method": "post",
                    "action_url": complete_url,
                    "fields": [
                        {
                            "name": "final_observations",
                            "type": "textarea",
                            "label": "Observacoes finais (obrigatorio)",
                            "required": True,
                        }
                    ],
                    "permission_domain": "work_orders",
                    "permission_action": "close",
                },
            )

    execution["operational_banner"] = None
    if so.status == ServiceOrder.Status.WAITING_PARTS:
        execution["operational_banner"] = {
            "tone": "warning",
            "title": "Execucao pausada: aguardando pecas",
            "body": "Registre apontamentos se necessario. Quando as pecas estiverem disponiveis, use a acao "
            "\"Pecas disponiveis — retomar execucao\" antes de encerrar a OS.",
        }
    elif so.status == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
        execution["operational_banner"] = {
            "tone": "warning",
            "title": "Aguardando aprovacao de orcamento",
            "body": "A continuidade depende da liberacao comercial. Apos aprovacao, use \"Orcamento aprovado — continuar\".",
        }

    execution["page_actions"] = page_actions
    execution["execution_readonly"] = readonly
    execution["checklist_save_url"] = checklist_url if checklist and not readonly else ""

    return {"work_order": order, "execution": execution}
