import unicodedata

from django.http import Http404

from apps.marketplace_ecom.catalog import (
    CATALOG_BRAND_PARTNERS,
    CATALOG_HOME_CATEGORIES,
    DEFAULT_IMAGE,
    resolve_catalog_image,
)
from apps.marketplace_ecom.models import TechnicalProduct

CATEGORY_IMAGE_BY_NAME = {item["filter_value"]: item["image"] for item in CATALOG_HOME_CATEGORIES}
BRAND_ROLE_BY_NAME = {item["name"]: item["role"] for item in CATALOG_BRAND_PARTNERS}


def normalize_specs(specs):
    if isinstance(specs, dict):
        return list(specs.items())
    return specs or []


def technical_product_to_catalog_entry(instance: TechnicalProduct) -> dict:
    description = instance.description or ""
    metadata = instance.metadata or {}
    static_image, featured_image_url = resolve_catalog_image(
        featured_image=instance.featured_image,
        catalog_image=metadata.get("catalog_image", ""),
    )

    return {
        "title": instance.title,
        "slug": instance.slug,
        "brand": instance.brand,
        "supplier": instance.supplier_name,
        "vendor": metadata.get("vendor", instance.brand),
        "category": instance.category,
        "product_type": metadata.get("product_type", "Solução técnica"),
        "short_description": instance.short_description,
        "technical_description": metadata.get("technical_description", description or instance.short_description),
        "description": description,
        "application_area": instance.application_area,
        "applications": metadata.get("applications", [instance.application_area]),
        "features": metadata.get("features", []),
        "specs": normalize_specs(metadata.get("specs", [])),
        "tags": metadata.get("tags", []),
        "price_label": "Sob consulta",
        "rating": "Sob consulta",
        "button_label": metadata.get("cta_label", "Solicitar orçamento"),
        "cta_label": metadata.get("cta_label", "Solicitar orçamento"),
        "lead_interest": metadata.get("lead_interest", f"{instance.brand} - {instance.title}"),
        "image": static_image,
        "is_featured": instance.is_featured,
        "featured_image_url": featured_image_url,
        "display_order": instance.display_order,
    }


def active_products_queryset():
    return (
        TechnicalProduct.objects.filter(is_active=True)
        .select_related("featured_image")
        .order_by("display_order", "-is_featured", "-updated_at")
    )


def get_active_products() -> list[dict]:
    return [technical_product_to_catalog_entry(row) for row in active_products_queryset()]


def get_featured_products(*, limit: int = 8) -> list[dict]:
    queryset = active_products_queryset().filter(is_featured=True)[:limit]
    return [technical_product_to_catalog_entry(row) for row in queryset]


def get_product_by_slug(slug: str) -> dict:
    if TechnicalProduct.objects.filter(slug=slug, is_active=False).exists():
        raise Http404("Produto nao encontrado")

    instance = active_products_queryset().filter(slug=slug).first()
    if instance is None:
        raise Http404("Produto nao encontrado")
    return technical_product_to_catalog_entry(instance)


def normalize_filter_value(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.casefold().strip()


def product_matches_query(product, query):
    searchable_fields = [
        product["title"],
        product["brand"],
        product["supplier"],
        product["category"],
        product["application_area"],
        product["short_description"],
        product.get("description", ""),
        product.get("technical_description", ""),
        product.get("product_type", ""),
        *product.get("applications", []),
        *product.get("features", []),
        *product.get("tags", []),
    ]
    normalized_query = normalize_filter_value(query)
    normalized_searchable = " ".join(normalize_filter_value(value) for value in searchable_fields)
    return all(term in normalized_searchable for term in normalized_query.split())


def filter_products(products, filters):
    filtered = list(products)
    if filters["q"]:
        filtered = [product for product in filtered if product_matches_query(product, filters["q"])]

    for field in ["brand", "supplier", "category"]:
        if filters[field]:
            filtered = [
                product for product in filtered
                if normalize_filter_value(product[field]) == normalize_filter_value(filters[field])
            ]

    if filters["application"]:
        filtered = [
            product for product in filtered
            if normalize_filter_value(filters["application"]) in {
                normalize_filter_value(value) for value in product.get("applications", [product["application_area"]])
            }
            or normalize_filter_value(filters["application"]) in {
                normalize_filter_value(value) for value in product.get("tags", [])
            }
        ]

    return filtered


def unique_values(products, field):
    return sorted({product[field] for product in products})


def unique_list_values(products, field):
    return sorted({value for product in products for value in product.get(field, [])})


def build_active_filters(filters):
    labels = {
        "q": "Busca",
        "brand": "Fabricante",
        "supplier": "Parceiro",
        "category": "Categoria",
        "application": "Aplicação",
    }
    return [
        {"label": labels[key], "value": value}
        for key, value in filters.items()
        if value
    ]


def build_home_categories(products: list[dict]) -> list[dict]:
    seen: set[str] = set()
    categories: list[dict] = []

    for product in products:
        category_name = product["category"]
        if category_name in seen:
            continue
        seen.add(category_name)
        categories.append(
            {
                "title": category_name,
                "image": CATEGORY_IMAGE_BY_NAME.get(category_name, product.get("image", DEFAULT_IMAGE)),
                "filter_param": "category",
                "filter_value": category_name,
            }
        )

    return sorted(categories, key=lambda item: item["title"])


def build_brand_partners(products: list[dict]) -> list[dict]:
    partners: list[dict] = []
    seen: set[str] = set()

    for product in products:
        brand_name = product["brand"]
        if brand_name in seen:
            continue
        seen.add(brand_name)
        partners.append(
            {
                "name": brand_name,
                "role": BRAND_ROLE_BY_NAME.get(brand_name, "Fabricante representado"),
            }
        )

    return sorted(partners, key=lambda item: item["name"])
