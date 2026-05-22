from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import DetailView, ListView, TemplateView

from .models import ErrorCode, TechnicalArticle, TechnicalCategory


class TechnicalPortalHomeView(LoginRequiredMixin, TemplateView):
    template_name = "technical_portal/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = TechnicalCategory.objects.filter(is_active=True)
        return context


class TechnicalPortalSearchView(LoginRequiredMixin, TemplateView):
    template_name = "technical_portal/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        articles = TechnicalArticle.objects.none()
        error_codes = ErrorCode.objects.none()

        if query:
            articles = (
                TechnicalArticle.objects.select_related("category")
                .filter(is_active=True, category__is_active=True)
                .filter(
                    Q(title__icontains=query)
                    | Q(summary__icontains=query)
                    | Q(content__icontains=query)
                    | Q(tags__icontains=query)
                )
            )
            error_codes = (
                ErrorCode.objects.select_related("category")
                .filter(is_active=True, category__is_active=True)
                .filter(
                    Q(code__icontains=query)
                    | Q(title__icontains=query)
                    | Q(brand__icontains=query)
                    | Q(model__icontains=query)
                    | Q(probable_cause__icontains=query)
                    | Q(recommended_action__icontains=query)
                    | Q(equipment_type__icontains=query)
                )
            )

        context["query"] = query
        context["articles"] = articles
        context["error_codes"] = error_codes
        context["result_count"] = articles.count() + error_codes.count()
        return context


class TechnicalCategoryDetailView(LoginRequiredMixin, DetailView):
    model = TechnicalCategory
    template_name = "technical_portal/category_detail.html"
    context_object_name = "category"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return TechnicalCategory.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        context["articles"] = category.articles.filter(is_active=True)
        context["error_codes"] = category.error_codes.filter(is_active=True)
        return context
