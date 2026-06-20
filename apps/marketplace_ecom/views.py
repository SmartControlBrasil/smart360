import unicodedata

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.growth_engine.models import Lead, LeadInteraction, LeadSource

from .forms import MarketplaceQuoteRequestForm
from .selectors import (
    build_active_filters,
    build_brand_partners,
    build_home_categories,
    filter_products,
    get_active_products,
    get_featured_products,
    get_product_by_slug,
    unique_list_values,
    unique_values,
)


class MarketplaceHomeView(TemplateView):
    template_name = "marketplace_ecom/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = get_active_products()
        context["products"] = products
        context["featured_products"] = get_featured_products()
        context["categories"] = build_home_categories(products)
        context["brand_partners"] = build_brand_partners(products)
        return context


class ProductListView(TemplateView):
    template_name = "marketplace_ecom/products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = get_active_products()
        filters = {
            "q": self.request.GET.get("q", "").strip(),
            "brand": self.request.GET.get("brand", "").strip(),
            "supplier": self.request.GET.get("supplier", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "application": self.request.GET.get("application", "").strip(),
        }
        filtered_products = filter_products(products, filters)

        context["products"] = filtered_products
        context["categories"] = build_home_categories(products)
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
        product = get_product_by_slug(self.kwargs["slug"])
        context = super().get_context_data(**kwargs)
        context["product"] = product
        context["quote_form"] = kwargs.get("quote_form") or MarketplaceQuoteRequestForm()
        active_products = get_active_products()
        context["related_products"] = [
            item for item in active_products if item["slug"] != product["slug"] and item["category"] == product["category"]
        ][:3]
        if not context["related_products"]:
            context["related_products"] = [item for item in active_products if item["slug"] != product["slug"]][:3]
        return context


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


class MarketplaceQuoteRequestView(View):
    def post(self, request, slug):
        product = get_product_by_slug(slug)
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
