import unicodedata

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.growth_engine.models import Lead, LeadInteraction, LeadSource
from apps.marketplace_ecom.models import TechnicalProduct

from .catalog import (
    CATALOG_BRAND_PARTNERS,
    CATALOG_HOME_CATEGORIES,
    DEFAULT_IMAGE,
    TECHNICAL_PRODUCTS,
    resolve_catalog_image,
)
from .forms import MarketplaceQuoteRequestForm

PRODUCTS = TECHNICAL_PRODUCTS


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
            if normalize_filter_value(filters["application"]) in {normalize_filter_value(value) for value in product.get("applications", [product["application_area"]])}
            or normalize_filter_value(filters["application"]) in {normalize_filter_value(value) for value in product.get("tags", [])}
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


def normalize_specs(specs):
    if isinstance(specs, dict):
        return list(specs.items())
    return specs or []


def technical_product_to_catalog_entry(instance: TechnicalProduct) -> dict:
    """Converte modelo persistido para o formato de catálogo usado pelos templates (dict)."""
    description = instance.description or ""
    metadata = instance.metadata or {}
    price_label = "Sob consulta"
    rating = "Sob consulta"
    button_label = "Solicitar orçamento"
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
        "price_label": price_label,
        "rating": rating,
        "button_label": metadata.get("cta_label", button_label),
        "cta_label": metadata.get("cta_label", button_label),
        "lead_interest": metadata.get("lead_interest", f"{instance.brand} - {instance.title}"),
        "image": static_image,
        "is_featured": instance.is_featured,
        "featured_image_url": featured_image_url,
    }


def merge_catalog_products() -> list:
    queryset = TechnicalProduct.objects.filter(is_active=True).select_related("featured_image").order_by(
        "-is_featured",
        "-updated_at",
    )
    merged: list[dict] = []
    consumed_slugs: set[str] = set()

    for row in queryset:
        merged.append(technical_product_to_catalog_entry(row))
        consumed_slugs.add(row.slug)

    for catalog_product in TECHNICAL_PRODUCTS:
        if catalog_product["slug"] in consumed_slugs:
            continue
        merged.append(catalog_product)

    return merged


def catalog_product_for_slug(slug: str) -> dict:
    if TechnicalProduct.objects.filter(slug=slug, is_active=False).exists():
        raise Http404("Produto nao encontrado")

    persisted = TechnicalProduct.objects.filter(slug=slug, is_active=True).select_related("featured_image").first()
    if persisted:
        return technical_product_to_catalog_entry(persisted)

    for catalog_product in TECHNICAL_PRODUCTS:
        if catalog_product["slug"] == slug:
            return catalog_product

    raise Http404("Produto nao encontrado")


def get_products():
    """Catálogo: produtos ativos persistidos (prioridade por slug), depois catálogo estático."""
    return merge_catalog_products()


def get_featured_products(products=None, limit=8):
    products = products or get_products()
    featured = [product for product in products if product.get("is_featured")]
    if featured:
        return featured[:limit]
    return products[:limit]


def get_product_or_404(slug: str):
    return catalog_product_for_slug(slug)


def get_marketplace_lead_source():
    source, _created = LeadSource.objects.get_or_create(
        name="marketplace_ecom",
        defaults={
            "source_type": LeadSource.SourceType.ORGANIC,
            "description": "Solicitações de orçamento geradas pelo catálogo técnico Smart360.",
        },
    )
    return source


def create_quote_request_lead(product, form):
    data = form.cleaned_data
    lead = Lead.objects.create(
        company_name=data["company"] or data["name"],
        contact_name=data["name"],
        email=data["email"],
        phone=data["phone"],
        whatsapp=data["phone"],
        city=data["city"],
        source=get_marketplace_lead_source(),
        status=Lead.Status.NEW,
        notes=data["message"],
        metadata={
            "product_slug": product["slug"],
            "product_title": product["title"],
            "brand": product["brand"],
            "supplier": product["supplier"],
            "category": product["category"],
            "product_type": product["product_type"],
            "application_area": product["application_area"],
            "origin": "marketplace_ecom",
            "request_type": "quote_request",
        },
    )
    LeadInteraction.objects.create(
        lead=lead,
        interaction_type=LeadInteraction.InteractionType.NOTE,
        channel=LeadInteraction.Channel.OTHER,
        summary="Solicitação de orçamento via catálogo técnico.",
    )
    return lead


class MarketplaceHomeView(TemplateView):
    template_name = "marketplace_ecom/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = get_products()
        context["products"] = products
        context["featured_products"] = get_featured_products(products)
        context["categories"] = CATALOG_HOME_CATEGORIES
        context["brand_partners"] = CATALOG_BRAND_PARTNERS
        return context


class ProductListView(TemplateView):
    template_name = "marketplace_ecom/products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = get_products()
        filters = {
            "q": self.request.GET.get("q", "").strip(),
            "brand": self.request.GET.get("brand", "").strip(),
            "supplier": self.request.GET.get("supplier", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "application": self.request.GET.get("application", "").strip(),
        }
        filtered_products = filter_products(products, filters)

        context["products"] = filtered_products
        context["categories"] = CATALOG_HOME_CATEGORIES
        context["brands"] = unique_values(products, "brand")
        context["suppliers"] = unique_values(products, "supplier")
        context["available_brands"] = context["brands"]
        context["available_suppliers"] = context["suppliers"]
        context["available_categories"] = unique_values(products, "category")
        context["available_applications"] = unique_list_values(products, "applications")
        context["active_filters"] = build_active_filters(filters)
        context["filters"] = filters
        context["result_count"] = len(filtered_products)
        return context


class ProductDetailView(TemplateView):
    template_name = "marketplace_ecom/product_detail.html"

    def get_context_data(self, **kwargs):
        product = get_product_or_404(self.kwargs["slug"])
        context = super().get_context_data(**kwargs)
        context["product"] = product
        context["quote_form"] = kwargs.get("quote_form") or MarketplaceQuoteRequestForm()
        context["related_products"] = [
            item for item in get_products() if item["slug"] != product["slug"] and item["category"] == product["category"]
        ][:3]
        if not context["related_products"]:
            context["related_products"] = [item for item in get_products() if item["slug"] != product["slug"]][:3]
        return context


class MarketplaceQuoteRequestView(View):
    def post(self, request, slug):
        product = get_product_or_404(slug)
        form = MarketplaceQuoteRequestForm(request.POST)
        if form.is_valid():
            create_quote_request_lead(product, form)
            messages.success(request, "Solicitação enviada. Nossa equipe comercial entrará em contato.")
            return redirect("marketplace_ecom:product-detail", slug=product["slug"])

        view = ProductDetailView()
        view.request = request
        view.kwargs = {"slug": slug}
        context = view.get_context_data(quote_form=form)
        return render(request, ProductDetailView.template_name, context, status=200)
