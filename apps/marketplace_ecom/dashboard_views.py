"""CRUD do Catálogo Técnico B2B no Admin Shell."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView

from apps.admin_shell.views import ShellContextMixin
from apps.marketplace_ecom.forms import TechnicalProductShellForm
from apps.marketplace_ecom.models import TechnicalProduct
from apps.marketplace_ecom.selectors import (
    admin_technical_products_queryset,
    filter_admin_technical_products,
    get_admin_product_filter_options,
    technical_product_to_catalog_entry,
)


class TechnicalCatalogBaseMixin(ShellContextMixin):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = True

    def get_breadcrumbs(self, tail_label=None):
        crumbs = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Catálogo Técnico B2B", "url": "admin-shell:technical-catalog-product-list"},
        ]
        if tail_label:
            crumbs.append({"label": tail_label, "url": None})
        return crumbs


class TechnicalProductListView(TechnicalCatalogBaseMixin, ListView):
    template_name = "admin_shell/technical_catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        queryset = admin_technical_products_queryset()
        self.filter_q = (self.request.GET.get("q") or "").strip()
        self.filter_brand = (self.request.GET.get("brand") or "").strip()
        self.filter_category = (self.request.GET.get("category") or "").strip()
        self.filter_status = self.request.GET.get("status") or "active"
        return filter_admin_technical_products(
            queryset,
            q=self.filter_q,
            brand=self.filter_brand,
            category=self.filter_category,
            status=self.filter_status,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        brands, categories = get_admin_product_filter_options()
        ctx["page_title"] = "Catálogo Técnico B2B"
        ctx["page_description"] = "Cadastro e operação dos produtos exibidos em /marketplace/."
        ctx["breadcrumbs"] = self.get_breadcrumbs()
        ctx["current_module_slug"] = "marketplace-technicians"
        ctx["search_q"] = self.filter_q
        ctx["filter_brand"] = self.filter_brand
        ctx["filter_category"] = self.filter_category
        ctx["filter_status"] = self.filter_status
        ctx["available_brands"] = brands
        ctx["available_categories"] = categories
        ctx["page_actions"] = [
            {
                "label": "Novo produto",
                "route_name": "admin-shell:technical-catalog-product-create",
                "permission_domain": "dashboard",
                "permission_action": "create",
            },
            {
                "label": "Biblioteca de imagens",
                "route_name": "admin-shell:media-image-list",
                "permission_domain": "dashboard",
                "permission_action": "view",
            },
        ]
        return ctx


class TechnicalProductCreateView(TechnicalCatalogBaseMixin, FormView):
    template_name = "admin_shell/technical_catalog/product_form.html"
    form_class = TechnicalProductShellForm
    permission_action = "create"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Novo produto técnico"
        ctx["page_description"] = "Cadastre uma solução para a vitrine pública do catálogo B2B."
        ctx["form_mode"] = "create"
        ctx["submit_label"] = "Salvar produto"
        ctx["cancel_url"] = reverse("admin-shell:technical-catalog-product-list")
        ctx["breadcrumbs"] = self.get_breadcrumbs("Novo produto")
        ctx["current_module_slug"] = "marketplace-technicians"
        return ctx

    def form_valid(self, form):
        product = form.save()
        messages.success(self.request, "Produto cadastrado com sucesso.")
        return redirect("admin-shell:technical-catalog-product-detail", pk=product.pk)


class TechnicalProductUpdateView(TechnicalCatalogBaseMixin, FormView):
    template_name = "admin_shell/technical_catalog/product_form.html"
    form_class = TechnicalProductShellForm
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(TechnicalProduct, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.product
        ctx["page_title"] = f"Editar — {self.product.title}"
        ctx["page_description"] = "Atualize os dados exibidos no catálogo público."
        ctx["form_mode"] = "update"
        ctx["submit_label"] = "Salvar alterações"
        ctx["cancel_url"] = reverse("admin-shell:technical-catalog-product-detail", kwargs={"pk": self.product.pk})
        ctx["breadcrumbs"] = self.get_breadcrumbs(self.product.title[:48])
        ctx["current_module_slug"] = "marketplace-technicians"
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Produto atualizado com sucesso.")
        return redirect("admin-shell:technical-catalog-product-detail", pk=self.product.pk)


class TechnicalProductDetailView(TechnicalCatalogBaseMixin, DetailView):
    model = TechnicalProduct
    template_name = "admin_shell/technical_catalog/product_detail.html"
    context_object_name = "product"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return admin_technical_products_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        catalog_entry = technical_product_to_catalog_entry(product)
        ctx["catalog_entry"] = catalog_entry
        ctx["page_title"] = product.title
        ctx["page_description"] = f"{product.brand} · {product.category}"
        ctx["breadcrumbs"] = self.get_breadcrumbs(product.title[:48])
        ctx["current_module_slug"] = "marketplace-technicians"
        ctx["public_product_url"] = reverse("marketplace_ecom:product-detail", kwargs={"slug": product.slug})
        ctx["public_catalog_url"] = reverse("marketplace_ecom:home")
        ctx["page_actions"] = [
            {
                "label": "Editar produto",
                "route_name": "admin-shell:technical-catalog-product-update",
                "route_kwargs": {"pk": product.pk},
                "permission_domain": "dashboard",
                "permission_action": "update",
            },
            {
                "label": "Ver no catálogo",
                "href": ctx["public_product_url"],
                "permission_domain": "dashboard",
                "permission_action": "view",
            },
        ]
        if product.is_active:
            ctx["page_actions"].append(
                {
                    "label": "Listagem pública",
                    "href": reverse("marketplace_ecom:products"),
                    "permission_domain": "dashboard",
                    "permission_action": "view",
                }
            )
        return ctx
