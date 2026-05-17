from __future__ import annotations

from collections import Counter
from django.utils import timezone

from apps.access_control_center.services.smart_system_access import filter_permissioned_items
from apps.ai_agents_center.services.technician_copilot import TechnicianCopilotService
from apps.marketplace_technicians.models import TechnicianAssignment
from apps.smart_system.models import Asset, ServiceOrder

from .smart_system_scheduling import get_technician_mobile_schedule_context
from .smart_system_work_order_execution import get_work_order_execution_context
from .smart_system_work_orders_domain import scoped_service_orders
from .smart_system_work_orders import serialize_work_order_row


TECHNICIAN_BOTTOM_NAV = [
    {
        "label": "Inicio",
        "url_name": "admin-shell:technician-app-dashboard",
        "match_names": ["admin-shell:technician-app-dashboard"],
        "permission_domain": "dashboard",
        "permission_action": "view",
    },
    {
        "label": "Agenda",
        "url_name": "admin-shell:technician-app-schedule",
        "match_names": ["admin-shell:technician-app-schedule"],
        "permission_domain": "scheduling",
        "permission_action": "view",
    },
    {
        "label": "Servicos",
        "url_name": "admin-shell:technician-app-services",
        "match_names": [
            "admin-shell:technician-app-services",
            "admin-shell:technician-app-service-detail",
            "admin-shell:technician-app-service-execution",
        ],
        "permission_domain": "work_orders",
        "permission_action": "view",
    },
    {
        "label": "Checklists",
        "url_name": "admin-shell:technician-app-checklists",
        "match_names": ["admin-shell:technician-app-checklists"],
        "permission_domain": "checklists",
        "permission_action": "view",
    },
    {
        "label": "Historico",
        "url_name": "admin-shell:technician-app-history",
        "match_names": ["admin-shell:technician-app-history"],
        "permission_domain": "work_orders",
        "permission_action": "view",
    },
    {
        "label": "Perfil",
        "url_name": "admin-shell:technician-app-profile",
        "match_names": ["admin-shell:technician-app-profile"],
        "permission_domain": "work_execution",
        "permission_action": "view",
    },
]


MARKETPLACE_ORDER_LINKS = {
    "OS-2026-0151": {
        "badge": "Marketplace",
        "summary": "Atendimento originado por atribuicao do marketplace de tecnicos.",
    }
}


def build_technician_app_context(request, tenant_context, permission_map):
    company = tenant_context.get("company")
    copilot_configuration = TechnicianCopilotService.get_configuration(company=company)
    current_name = getattr(getattr(request, "resolver_match", None), "view_name", "")
    nav_items = filter_permissioned_items(TECHNICIAN_BOTTOM_NAV, permission_map)
    for item in nav_items:
        item["is_active"] = current_name in item.get("match_names", [item["url_name"]])
    return {
        "mobile_nav": nav_items,
        "mobile_user": {
            "id": request.user.id,
            "name": request.user.display_name or request.user.full_name or request.user.email,
            "email": request.user.email,
            "initials": "".join(part[0] for part in (request.user.first_name, request.user.last_name) if part).upper()[:2] or "TM",
        },
        "mobile_tenant_context": tenant_context,
        "mobile_runtime_context": {
            "company": {
                "id": getattr(tenant_context.get("company"), "id", None),
                "name": getattr(tenant_context.get("company"), "name", ""),
            },
            "site": {
                "id": getattr(tenant_context.get("site"), "id", None),
                "name": getattr(tenant_context.get("site"), "name", ""),
            },
        },
        "mobile_quick_actions": [
            {"label": "Agenda", "href": "/field/schedule/", "permission_domain": "scheduling", "permission_action": "view"},
            {"label": "Servicos", "href": "/field/services/", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Checklist", "href": "/field/checklists/", "permission_domain": "checklists", "permission_action": "view"},
            {"label": "Sincronizacao", "href": "/field/sync/", "permission_domain": "work_execution", "permission_action": "execute"},
        ],
        "mobile_sync_endpoints": {
            "bundle": "/field/api/offline-bundle/",
            "sync": "/field/api/offline-sync/",
            "sync_center": "/field/sync/",
            "copilot_context": "/field/api/copilot/context/",
            "copilot_query": "/field/api/copilot/query/",
            "copilot_suggestions": "/field/api/copilot/suggestions/",
            "copilot_sync": "/field/api/copilot/sync/",
        },
        "mobile_copilot": {
            "enabled": copilot_configuration.is_enabled if copilot_configuration else True,
            "allow_offline_fallback": copilot_configuration.allow_offline_fallback if copilot_configuration else True,
        },
    }


def _technician_name(user):
    return user.display_name or user.full_name or user.email


def _assigned_records(user, tenant_context):
    qs = scoped_service_orders(request=None, tenant_context=tenant_context).exclude(status=ServiceOrder.Status.CANCELLED)
    if not user.is_superuser:
        qs = qs.filter(assigned_to=user)
    return [serialize_work_order_row(so) for so in qs.order_by("-opened_at")[:300]]


def get_technician_dashboard_context(user, tenant_context):
    records = _assigned_records(user, tenant_context)
    open_status_slugs = {
        ServiceOrder.Status.OPEN,
        ServiceOrder.Status.SCHEDULED,
        ServiceOrder.Status.ON_HOLD,
        ServiceOrder.Status.WAITING_PARTS,
        ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
    }
    in_progress_status_slugs = {ServiceOrder.Status.IN_PROGRESS}
    today_iso = timezone.localdate().isoformat()
    today_records = [record for record in records if record.get("opened_at_iso") == today_iso]
    recent_completed = [record for record in records if record.get("status_slug") == ServiceOrder.Status.COMPLETED][:4]
    pending_checklists = []
    for record in records:
        if not record.get("has_checklist"):
            continue
        ex = get_work_order_execution_context(record["code"], tenant_context=tenant_context)
        if ex and ex.get("execution", {}).get("checklist"):
            pending_checklists.append(record)
    return {
        "dashboard_cards": [
            {"label": "Atribuidas hoje", "value": len(today_records), "meta": "servicos que exigem acao no dia", "tone": "indigo"},
            {"label": "Em andamento", "value": sum(1 for record in records if record.get("status_slug") in in_progress_status_slugs), "meta": "execucoes de campo ativas", "tone": "sky"},
            {"label": "Pendentes", "value": sum(1 for record in records if record.get("status_slug") in open_status_slugs), "meta": "ordens aguardando inicio", "tone": "amber"},
            {"label": "Checklists pendentes", "value": len(pending_checklists), "meta": "rotinas com checklist vinculado", "tone": "emerald"},
        ],
        "today_services": today_records[:5],
        "recent_completed": recent_completed,
        "operational_alerts": _build_mobile_alerts(records),
        "page_actions": [
            {"label": "Agenda de hoje", "href": "/field/schedule/"},
            {"label": "Ver servicos", "href": "/field/services/"},
            {"label": "Checklists", "href": "/field/checklists/"},
        ],
    }


def get_technician_service_listing_context(user, tenant_context, filters):
    records = _assigned_records(user, tenant_context)
    filter_name = filters.get("preset", "")
    if filter_name == "today":
        records = [record for record in records if record.get("opened_at_iso") == timezone.localdate().isoformat()]
    elif filter_name == "pending":
        records = [
            record
            for record in records
            if record.get("status_slug")
            in {
                ServiceOrder.Status.OPEN,
                ServiceOrder.Status.SCHEDULED,
                ServiceOrder.Status.ON_HOLD,
                ServiceOrder.Status.WAITING_PARTS,
                ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
            }
        ]
    elif filter_name == "in_progress":
        records = [record for record in records if record.get("status_slug") == ServiceOrder.Status.IN_PROGRESS]
    elif filter_name == "completed":
        records = [record for record in records if record.get("status_slug") == ServiceOrder.Status.COMPLETED]
    if filters.get("search"):
        term = filters["search"].lower()
        records = [
            record for record in records
            if term in record["code"].lower()
            or term in record["title"].lower()
            or term in record["asset_code"].lower()
            or term in record["client"].lower()
        ]
    return {
        "service_filters": filters,
        "service_cards": [
            {
                **record,
                "detail_url": f"/field/services/{record['code']}/",
                "marketplace": MARKETPLACE_ORDER_LINKS.get(record["code"]),
            }
            for record in records
        ],
    }


def get_technician_service_detail_context(user, tenant_context, order_code):
    record = next((item for item in _assigned_records(user, tenant_context) if item["code"] == order_code), None)
    if record is None:
        return None
    execution = get_work_order_execution_context(order_code, tenant_context=tenant_context)
    if execution is None:
        return None
    checklist = execution["execution"]["checklist_execution"]
    return {
        "service": {
            **record,
            "asset_name": record.get("asset_name") or record["title"],
            "marketplace": MARKETPLACE_ORDER_LINKS.get(record["code"]),
        },
        "execution": execution["execution"],
        "checklist_summary": checklist,
        "maintenance_recommendations": _maintenance_recommendations_for_record(record, tenant_context),
        "recommended_parts": _recommended_parts_for_execution(execution["execution"]),
        "copilot_suggestions": [],
        "page_actions": [
            {"label": "Iniciar execucao", "href": f"/field/services/{order_code}/start/"},
            {"label": "Abrir checklist", "href": f"/field/services/{order_code}/execute/"},
            {"label": "Concluir", "href": f"/field/services/{order_code}/complete/"},
        ],
    }


def get_technician_copilot_bootstrap(detail_context):
    if detail_context is None:
        return {"context": {}, "suggestions": [], "maintenance_recommendations": [], "recommended_parts": []}
    detail_context["copilot_suggestions"] = TechnicianCopilotService.get_suggestions(
        context=TechnicianCopilotService.resolve_context(service_payload=detail_context, offline=False)
    )
    return TechnicianCopilotService.build_bootstrap(service_payload=detail_context)


def get_technician_execution_context(user, tenant_context, order_code):
    detail = get_technician_service_detail_context(user, tenant_context, order_code)
    if detail is None:
        return None
    execution = detail["execution"]
    progress = execution["checklist_execution"]
    return {
        **detail,
        "execution_steps": [
            {"slug": "start", "label": "Inicio", "done": bool(execution["started_at"] and execution["started_at"] != "Aguardando inicio")},
            {"slug": "checklist", "label": "Checklist", "done": progress.get("responded_count", 0) > 0},
            {"slug": "diagnosis", "label": "Diagnostico", "done": bool(execution["diagnosis"].get("technical_diagnosis"))},
            {"slug": "action", "label": "Acao", "done": bool(execution["executed_action"].get("intervention"))},
            {"slug": "materials", "label": "Materiais", "done": bool(execution["materials"])},
            {"slug": "evidence", "label": "Evidencias", "done": bool(execution["evidence"])},
            {"slug": "signature", "label": "Assinaturas", "done": execution["signatures"].get("has_technician_signature") and execution["signatures"].get("has_client_resolution")},
            {"slug": "finish", "label": "Conclusao", "done": execution.get("status_slug") == ServiceOrder.Status.COMPLETED},
        ],
        "progress_cards": [
            {"label": "Execucao", "value": f"{execution['progress']}%", "meta": execution["status"], "tone": "indigo"},
            {"label": "OK", "value": progress.get("ok_count", 0), "meta": "itens conformes", "tone": "emerald"},
            {"label": "NOK", "value": progress.get("nok_count", 0), "meta": "anomalias encontradas", "tone": "red"},
            {"label": "Pendentes", "value": progress.get("pending_count", 0), "meta": "itens nao respondidos", "tone": "amber"},
            {
                "label": "Assinaturas",
                "value": f"{int(execution['signatures']['has_technician_signature']) + int(execution['signatures']['has_client_signature'])}/2",
                "meta": "tecnico e cliente",
                "tone": "violet",
            },
        ],
    }


def get_technician_checklist_listing_context(user, tenant_context):
    records = []
    for record in _assigned_records(user, tenant_context):
        execution = get_work_order_execution_context(record["code"], tenant_context=tenant_context)
        if not execution:
            continue
        checklist = execution["execution"]["checklist"]
        if not checklist:
            continue
        records.append(
            {
                "order_code": record["code"],
                "title": checklist["name"],
                "checklist_code": checklist["code"],
                "asset_code": record["asset_code"],
                "status": execution["execution"]["status"],
                "progress": execution["execution"]["checklist_execution"]["progress"],
                "execute_url": f"/field/services/{record['code']}/execute/",
            }
        )
    return {"checklist_cards": records}


def get_technician_history_context(user, tenant_context):
    records = [record for record in _assigned_records(user, tenant_context) if record.get("status_slug") == ServiceOrder.Status.COMPLETED]
    return {"history_records": records[:8]}


def get_technician_profile_context(user, tenant_context):
    records = _assigned_records(user, tenant_context)
    completed = [record for record in records if record.get("status_slug") == ServiceOrder.Status.COMPLETED]
    ratings = []
    try:
        technician_assignments = TechnicianAssignment.objects.filter(
            technician_profile__user=user,
            assignment_status=TechnicianAssignment.AssignmentStatus.COMPLETED,
        ).select_related("technician_profile")
        ratings = [assignment.customer_rating for assignment in technician_assignments if assignment.customer_rating]
    except Exception:
        ratings = []
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 4.8
    categories = Counter(record["maintenance_type"] for record in records)
    return {
        "profile_cards": [
            {"label": "Servicos concluidos", "value": len(completed), "meta": "historico recente do tecnico", "tone": "emerald"},
            {"label": "Em andamento", "value": sum(1 for record in records if record.get("status_slug") == ServiceOrder.Status.IN_PROGRESS), "meta": "ordens ativas", "tone": "sky"},
            {"label": "Avaliacao media", "value": avg_rating, "meta": "servicos internos e marketplace", "tone": "amber"},
        ],
        "service_mix": [{"label": label, "value": value} for label, value in categories.items()],
    }


def get_technician_offline_bundle_context(user, tenant_context):
    listing = get_technician_service_listing_context(user, tenant_context, {})
    schedule = get_technician_mobile_schedule_context(user=user, tenant_context=tenant_context)
    service_details = []
    for service in listing["service_cards"]:
        detail = get_technician_service_detail_context(user, tenant_context, service["code"])
        if detail:
            detail["copilot_suggestions"] = TechnicianCopilotService.get_suggestions(
                context=TechnicianCopilotService.resolve_context(service_payload=detail, offline=False)
            )
            service_details.append(
                {
                    "service": detail["service"],
                    "execution": {
                        "execution_code": detail["execution"]["execution_code"],
                        "status": detail["execution"]["status"],
                        "progress": detail["execution"]["progress"],
                        "started_at": detail["execution"]["started_at"],
                        "finished_at": detail["execution"]["finished_at"],
                        "checklist_execution": detail["execution"]["checklist_execution"],
                        "diagnosis": detail["execution"]["diagnosis"],
                        "executed_action": detail["execution"]["executed_action"],
                        "materials": detail["execution"]["materials"],
                        "evidence": detail["execution"]["evidence"],
                        "finalization": detail["execution"]["finalization"],
                        "offline_sync": detail["execution"].get("offline_sync", {}),
                    },
                    "maintenance_recommendations": detail["maintenance_recommendations"],
                    "recommended_parts": detail["recommended_parts"],
                    "copilot_suggestions": detail["copilot_suggestions"],
                }
            )
    return {
        "generated_at": timezone.now().isoformat(),
        "services": listing["service_cards"],
        "service_details": service_details,
        "checklists": get_technician_checklist_listing_context(user, tenant_context)["checklist_cards"],
        "history": get_technician_history_context(user, tenant_context)["history_records"],
        "schedule": schedule,
    }


def _maintenance_recommendations_for_record(record, tenant_context):
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    asset_public_id = record.get("asset_public_id", "")
    if not asset_public_id:
        asset = Asset.objects.filter(asset_tag=record.get("asset_code", "")).select_related("operational_site").first()
        asset_public_id = str(asset.public_id) if asset else ""
        if site is None and asset is not None:
            site = asset.operational_site
    if not asset_public_id:
        return []
    return TechnicianCopilotService.maintenance_recommendations_for_asset(
        company=company,
        site=site,
        asset_public_id=asset_public_id,
    )


def _recommended_parts_for_execution(execution):
    materials = execution.get("materials", [])
    recommendations = []
    if execution.get("diagnosis", {}).get("components"):
        for material in materials[:3]:
            recommendations.append(
                {
                    "code": material["code"],
                    "name": material["name"],
                    "reason": "Historico local de material relacionado ao diagnostico atual.",
                }
            )
    if not recommendations and materials:
        for material in materials[:2]:
            recommendations.append(
                {
                    "code": material["code"],
                    "name": material["name"],
                    "reason": "Material ja utilizado ou reservado em atendimento similar.",
                }
            )
    return recommendations


def _build_mobile_alerts(records):
    from apps.smart_system.models import Asset

    alerts = []
    for record in records:
        if record.get("status_slug") == ServiceOrder.Status.WAITING_PARTS:
            alerts.append({"title": record["code"], "description": "Atendimento aguardando material.", "tone": "warning"})
        if record.get("criticality_slug") == Asset.Criticality.CRITICAL:
            alerts.append({"title": record["code"], "description": "Ativo critico exige prioridade de campo.", "tone": "critical"})
        if len(alerts) >= 4:
            break
    return alerts


def get_technician_schedule_page_context(user, tenant_context):
    return get_technician_mobile_schedule_context(user=user, tenant_context=tenant_context)
