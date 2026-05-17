"""Pacote comercial MVP a partir de Template.metadata (JSON), sem migrations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _template_metadata_dict(template) -> dict[str, Any]:
    if template is None:
        return {}
    raw = getattr(template, "metadata", None)
    if raw is None or not isinstance(raw, dict):
        return {}
    return raw


def resolve_package_price(template) -> Decimal | None:
    """Preco unico para UI e persistencia: list_price em metadata, senao base_price."""
    if template is None:
        return None
    md = _template_metadata_dict(template)
    raw = md.get("list_price")
    if raw is not None and raw != "":
        try:
            price = Decimal(str(raw))
            if price > 0:
                return price
        except (InvalidOperation, ValueError, TypeError):
            pass
    try:
        return template.base_price
    except Exception:
        return None


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return [str(value).strip()]


def extract_package_catalog(template) -> dict[str, Any]:
    """Extrai campos comerciais do Template.metadata."""
    md = _template_metadata_dict(template)
    return {
        "package_code": str(md.get("package_code") or "").strip(),
        "tier": str(md.get("tier") or "").strip(),
        "commercial_name": str(md.get("commercial_name") or "").strip(),
        "short_description": str(md.get("short_description") or "").strip(),
        "deliverables": _coerce_str_list(md.get("deliverables")),
        "upsells": _coerce_str_list(md.get("upsells")),
        "list_price": md.get("list_price"),
        "display_price": resolve_package_price(template),
    }


def build_package_snapshot(template) -> dict[str, Any]:
    """Snapshot para SiteOrder.metadata['package_snapshot']."""
    if template is None:
        return {}
    cat = extract_package_catalog(template)
    price = cat["display_price"]
    return {
        "package_code": cat["package_code"],
        "commercial_name": cat["commercial_name"] or template.name,
        "tier": cat["tier"],
        "deliverables": cat["deliverables"],
        "upsells": cat["upsells"],
        "price": str(price) if price is not None else "",
        "template_id": template.id,
        "template_name": template.name,
    }


def format_template_choice_label(template) -> str:
    """Rotulo amigavel: nome comercial + preco."""
    if template is None:
        return ""
    cat = extract_package_catalog(template)
    name = cat["commercial_name"] or template.name
    price = cat["display_price"]
    suffix = f" — R$ {price:.2f}" if price is not None else ""
    return f"{name}{suffix}"


def template_choice_hint(template) -> str:
    """Texto explicativo para o formulario (plain text)."""
    if template is None:
        return ""
    cat = extract_package_catalog(template)
    parts: list[str] = []
    if cat["short_description"]:
        parts.append(cat["short_description"])
    if cat["deliverables"]:
        parts.append("Entregaveis: " + ", ".join(cat["deliverables"][:8]))
    if cat["upsells"]:
        parts.append("Upsells: " + ", ".join(cat["upsells"][:6]))
    return "\n".join(parts)


def package_hints_map(templates_queryset) -> dict[str, str]:
    return {str(t.pk): template_choice_hint(t) for t in templates_queryset}


def resolve_commercial_package_for_order(order) -> dict[str, Any] | None:
    """Dados para o bloco Pacote comercial no detalhe (snapshot ou template)."""
    md = getattr(order, "metadata", None) or {}
    if not isinstance(md, dict):
        md = {}
    snap = md.get("package_snapshot")
    if isinstance(snap, dict) and snap:
        name = str(snap.get("commercial_name") or "").strip()
        if not name:
            name = str(snap.get("template_name") or "").strip()
        return {
            "commercial_name": name,
            "tier": str(snap.get("tier") or "").strip(),
            "deliverables": _coerce_str_list(snap.get("deliverables")),
            "upsells": _coerce_str_list(snap.get("upsells")),
            "price_display": str(snap.get("price") or "").strip(),
            "package_code": str(snap.get("package_code") or "").strip(),
            "source": "snapshot",
        }
    tpl = getattr(order, "selected_template", None)
    if tpl is not None:
        cat = extract_package_catalog(tpl)
        price = resolve_package_price(tpl)
        return {
            "commercial_name": cat["commercial_name"] or tpl.name,
            "tier": cat["tier"],
            "deliverables": cat["deliverables"],
            "upsells": cat["upsells"],
            "price_display": str(price) if price is not None else "",
            "package_code": cat["package_code"],
            "source": "template",
        }
    return None


def order_package_chart_label(order) -> str:
    """Rotulo para agrupamento no dashboard (nome comercial ou codigo)."""
    pkg = resolve_commercial_package_for_order(order)
    if not pkg:
        return "Sem pacote"
    code = pkg.get("package_code") or ""
    name = pkg.get("commercial_name") or ""
    if code and name:
        return f"{name} ({code})"
    return name or code or "Sem pacote"


def final_price_should_use_template_default(value) -> bool:
    """True quando final_price deve ser preenchido pelo pacote/template."""
    if value is None or value == "":
        return True
    if value == 0:
        return True
    try:
        return Decimal(str(value)) == 0
    except Exception:
        return False
