"""Contextos SSR para inventario operacional de equipamentos do cliente."""

from __future__ import annotations

from apps.smart_system.models import CustomerEquipment
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _serialize_customer_equipment(row: CustomerEquipment) -> dict:
    display_name = row.display_name or row.equipment_model.name
    return {
        "code": str(row.public_id)[:8].upper(),
        "display_name": display_name,
        "customer_tag": row.customer_tag,
        "full_label": f"{display_name} — TAG: {row.customer_tag}",
        "company": row.company.name,
        "site": row.site.name,
        "equipment_model": row.equipment_model.name,
        "status": row.get_status_display(),
        "status_slug": row.status,
        "location": row.location or "—",
        "internal_code": row.internal_code or "—",
        "serial_number": row.serial_number or "—",
        "preventive_group": row.preventive_group or "—",
        "is_pmoc_applicable": bool(row.is_pmoc_applicable),
        "installed_at": row.installed_at.strftime("%d/%m/%Y") if row.installed_at else "—",
        "notes": row.notes or "",
        "created_at": row.created_at.strftime("%d/%m/%Y %H:%M"),
        "updated_at": row.updated_at.strftime("%d/%m/%Y %H:%M"),
    }


def get_customer_equipment_listing_context(*, request, tenant_context=None):
    queryset = SmartSystemScopeService.scope_queryset(
        CustomerEquipment.objects.select_related("company", "site", "equipment_model", "equipment_model__category"),
        request,
    ).order_by("site__name", "customer_tag")
    records = [_serialize_customer_equipment(row) for row in queryset]
    total = len(records)
    return {
        "customer_equipments": records,
        "customer_equipment_kpis": [
            {"label": "Inventario ativo", "value": str(total), "meta": "equipamentos vinculados por cliente/site", "tone": "indigo"},
            {
                "label": "Grupo preventivo A/B/C",
                "value": str(sum(1 for row in records if row["preventive_group"] in {"A", "B", "C"})),
                "meta": "base para divisão de visitas",
                "tone": "sky",
            },
            {
                "label": "Com PMOC aplicável",
                "value": str(sum(1 for row in records if row["is_pmoc_applicable"])),
                "meta": "rotina regulatória monitorada",
                "tone": "emerald",
            },
            {
                "label": "Sem localização",
                "value": str(sum(1 for row in records if row["location"] == "—")),
                "meta": "recomendado completar cadastro",
                "tone": "amber",
            },
        ],
        "page_actions": [
            {"label": "Novo equipamento do cliente", "route_name": "admin-shell:smart-system-customer-equipment-create", "permission_domain": "assets", "permission_action": "create"},
            {"label": "Modelos técnicos", "route_name": "admin-shell:smart-system-equipment-models", "permission_domain": "assets", "permission_action": "view"},
        ],
    }


def get_customer_equipment_detail_context(*, request, equipment_code: str, tenant_context=None):
    queryset = SmartSystemScopeService.scope_queryset(
        CustomerEquipment.objects.select_related("company", "site", "equipment_model", "equipment_model__category"),
        request,
    )
    equipment = queryset.filter(public_id__startswith=equipment_code).first()
    if equipment is None:
        return None
    payload = _serialize_customer_equipment(equipment)
    payload["equipment_model_part_links"] = [
        {
            "part_code": rel.part.code,
            "part_name": rel.part.name,
            "quantity_default": str(rel.quantity_default),
            "notes": rel.notes or "—",
        }
        for rel in equipment.equipment_model.parts.select_related("part").all().order_by("part__name")
    ]
    payload["todo_notes"] = [
        "TODO: integrar abertura de OS selecionando CustomerEquipment no lugar de Asset.",
        "TODO: integrar preventivas por grupo A/B/C com ciclo automático por site.",
    ]
    payload["page_actions"] = [
        {"label": "Editar inventário", "route_name": "admin-shell:smart-system-customer-equipment-update", "route_kwargs": {"equipment_code": equipment_code}, "permission_domain": "assets", "permission_action": "update"},
        {"label": "Voltar à lista", "route_name": "admin-shell:smart-system-customer-equipments", "permission_domain": "assets", "permission_action": "view"},
    ]
    return payload
