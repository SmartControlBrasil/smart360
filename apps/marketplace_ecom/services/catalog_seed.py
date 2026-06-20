from apps.marketplace_ecom.catalog import TECHNICAL_PRODUCTS
from apps.marketplace_ecom.models import TechnicalProduct


def catalog_entry_to_product_defaults(entry: dict, *, display_order: int = 0) -> dict:
    metadata = {
        "product_type": entry.get("product_type", "Solução técnica"),
        "applications": entry.get("applications", []),
        "features": entry.get("features", []),
        "specs": entry.get("specs", []),
        "tags": entry.get("tags", []),
        "catalog_image": entry.get("image", ""),
        "technical_description": entry.get("technical_description", entry.get("short_description", "")),
        "vendor": entry.get("vendor", entry.get("brand", "")),
        "cta_label": entry.get("cta_label", "Solicitar orçamento"),
        "lead_interest": entry.get("lead_interest", f"{entry.get('brand', '')} - {entry.get('title', '')}"),
    }
    return {
        "title": entry["title"],
        "brand": entry["brand"],
        "supplier_name": entry.get("supplier", "Smart Control Brasil"),
        "category": entry["category"],
        "short_description": entry["short_description"],
        "description": entry.get("description", entry["short_description"]),
        "application_area": entry.get("application_area", ", ".join(entry.get("applications", []))),
        "is_active": True,
        "is_featured": entry.get("is_featured", False),
        "display_order": display_order,
        "metadata": metadata,
    }


def upsert_technical_product_from_catalog_entry(
    entry: dict,
    *,
    display_order: int = 0,
) -> tuple[TechnicalProduct, bool]:
    defaults = catalog_entry_to_product_defaults(entry, display_order=display_order)
    return TechnicalProduct.objects.update_or_create(slug=entry["slug"], defaults=defaults)


def seed_technical_catalog_from_static(*, starting_order: int = 10, step: int = 10) -> dict[str, int]:
    created = 0
    updated = 0
    order = starting_order

    for entry in TECHNICAL_PRODUCTS:
        _, was_created = upsert_technical_product_from_catalog_entry(entry, display_order=order)
        created += int(was_created)
        updated += int(not was_created)
        order += step

    return {"created": created, "updated": updated, "total": len(TECHNICAL_PRODUCTS)}
