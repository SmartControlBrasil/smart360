"""Contextos SSR para catalogo tecnico de modelos de equipamento."""

from __future__ import annotations

from apps.smart_system.models import EquipmentModel
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _serialize_equipment_model(row: EquipmentModel) -> dict:
    category_name = row.category.name if row.category else "Sem categoria"
    return {
        "code": str(row.public_id)[:8].upper(),
        "name": row.name,
        "company": row.company.name,
        "category": category_name,
        "manufacturer": row.manufacturer or "—",
        "equipment_type": row.equipment_type or "—",
        "status": row.get_status_display(),
        "status_slug": row.status,
        "is_pmoc_applicable": row.is_pmoc_applicable,
        "pmoc_frequency": row.pmoc_frequency or "—",
        "notes": row.notes or "",
        "parts_count": row.parts.count(),
        "created_at": row.created_at.strftime("%d/%m/%Y %H:%M"),
        "updated_at": row.updated_at.strftime("%d/%m/%Y %H:%M"),
    }


def get_equipment_model_listing_context(*, request, tenant_context=None):
    queryset = SmartSystemScopeService.scope_queryset(
        EquipmentModel.objects.select_related("company", "category").prefetch_related("parts"),
        request,
    ).order_by("name")

    records = [_serialize_equipment_model(row) for row in queryset]
    total = len(records)
    pmoc_enabled = sum(1 for row in records if row["is_pmoc_applicable"])

    return {
        "equipment_models": records,
        "equipment_model_kpis": [
            {"label": "Modelos catalogados", "value": str(total), "meta": "catalogo tecnico corporativo", "tone": "indigo"},
            {"label": "Modelos PMOC", "value": str(pmoc_enabled), "meta": "com rotina regulatoria sugerida", "tone": "emerald"},
            {
                "label": "Com peças mapeadas",
                "value": str(sum(1 for row in records if row["parts_count"] > 0)),
                "meta": "base para manutenção corretiva",
                "tone": "sky",
            },
            {"label": "Sem categoria", "value": str(sum(1 for row in records if row["category"] == "Sem categoria")), "meta": "ajuste recomendado", "tone": "amber"},
        ],
        "page_actions": [
            {"label": "Novo modelo", "route_name": "admin-shell:smart-system-equipment-model-create", "permission_domain": "assets", "permission_action": "create"},
            {"label": "Ativos legados", "route_name": "admin-shell:smart-system-assets", "permission_domain": "assets", "permission_action": "view"},
        ],
    }


def get_equipment_model_detail_context(*, request, model_code: str, tenant_context=None):
    queryset = SmartSystemScopeService.scope_queryset(
        EquipmentModel.objects.select_related("company", "category").prefetch_related("parts", "parts__part"),
        request,
    )
    model = queryset.filter(public_id__startswith=model_code).first()
    if model is None:
        return None
    payload = _serialize_equipment_model(model)
    payload["parts"] = [
        {
            "part_code": rel.part.code,
            "part_name": rel.part.name,
            "quantity_default": str(rel.quantity_default),
            "notes": rel.notes or "—",
        }
        for rel in model.parts.all().order_by("part__name")
    ]
    payload["todo_notes"] = [
        "TODO: conectar ServiceOrder ao CustomerEquipment sem depender de Asset legado.",
        "TODO: incluir migração assistida de Asset para CustomerEquipment em fase futura.",
    ]
    payload["page_actions"] = [
        {"label": "Editar modelo", "route_name": "admin-shell:smart-system-equipment-model-update", "route_kwargs": {"model_code": model_code}, "permission_domain": "assets", "permission_action": "update"},
        {"label": "Voltar à lista", "route_name": "admin-shell:smart-system-equipment-models", "permission_domain": "assets", "permission_action": "view"},
    ]
    return payload
