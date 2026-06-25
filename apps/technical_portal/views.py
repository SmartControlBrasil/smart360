from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.smart_system.models import Asset, ServiceOrder, WorkLog
from apps.smart_system.services.maintenance_service import ServiceOrderService

from .forms import ClientServiceOrderForm
from .models import ErrorCode, TechnicalArticle, TechnicalCategory
from .services import (
    allowed_assets,
    allowed_service_orders,
    attach_portal_visits_to_orders,
    get_next_portal_visit,
    get_service_order_portal_visit,
    user_can_access_service_order,
    user_can_create_service_order,
)


IN_PROGRESS_STATUSES = (
    ServiceOrder.Status.SCHEDULED,
    ServiceOrder.Status.IN_PROGRESS,
    ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
    ServiceOrder.Status.WAITING_PARTS,
    ServiceOrder.Status.ON_HOLD,
)


class ClientPortalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "client_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = allowed_service_orders(self.request)
        assets = allowed_assets(self.request)

        status_rows = list(orders.values("status").annotate(total=Count("id")).order_by("status"))
        type_rows = list(orders.values("maintenance_type").annotate(total=Count("id")).order_by("maintenance_type"))
        month_rows = list(
            orders.annotate(month=TruncMonth("opened_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")[:12]
        )

        context.update(
            {
                "open_count": orders.filter(status=ServiceOrder.Status.OPEN).count(),
                "in_progress_count": orders.filter(status__in=IN_PROGRESS_STATUSES).count(),
                "completed_count": orders.filter(status=ServiceOrder.Status.COMPLETED).count(),
                "asset_count": assets.count(),
                "stopped_asset_count": assets.filter(status=Asset.Status.STOPPED).count(),
                "latest_orders": orders[:6],
                "next_portal_visit": get_next_portal_visit(self.request),
                "can_create_service_order": user_can_create_service_order(self.request),
                "status_chart": {
                    "labels": [ServiceOrder.Status(row["status"]).label for row in status_rows],
                    "series": [row["total"] for row in status_rows],
                },
                "type_chart": {
                    "labels": [ServiceOrder.MaintenanceType(row["maintenance_type"]).label for row in type_rows],
                    "series": [row["total"] for row in type_rows],
                },
                "month_chart": {
                    "labels": [row["month"].strftime("%m/%Y") if row["month"] else "Sem data" for row in month_rows],
                    "series": [row["total"] for row in month_rows],
                },
                "has_scope_data": orders.exists() or assets.exists(),
            }
        )
        return context


class ClientServiceOrderCreateView(LoginRequiredMixin, FormView):
    template_name = "client_portal/service_order_form.html"
    form_class = ClientServiceOrderForm
    success_url = reverse_lazy("technical_portal:service-orders")

    def dispatch(self, request, *args, **kwargs):
        if not user_can_create_service_order(request):
            raise PermissionDenied("Seu perfil permite acompanhar chamados, mas nao abrir novos chamados.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        site = form.cleaned_data["operational_site"]
        asset = form.cleaned_data.get("asset")
        description = form.cleaned_data["description"].strip()
        title = description.splitlines()[0][:180] or "Chamado aberto pelo portal"

        ServiceOrderService.create_service_order(
            user=self.request.user,
            validated_data={
                "client": site.maintenance_client,
                "operational_site": site,
                "asset": asset,
                "maintenance_type": ServiceOrder.MaintenanceType.CORRECTIVE,
                "priority": form.cleaned_data["priority"],
                "status": ServiceOrder.Status.OPEN,
                "source": ServiceOrder.Source.MANUAL,
                "title": title,
                "description": description,
                "requested_by": getattr(self.request.user, "full_name", "") or getattr(self.request.user, "email", "") or str(self.request.user),
            },
        )
        messages.success(self.request, "Chamado aberto com sucesso.")
        return super().form_valid(form)


class ClientServiceOrderListView(LoginRequiredMixin, ListView):
    template_name = "client_portal/service_order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        return allowed_service_orders(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attach_portal_visits_to_orders(self.request, context["orders"])
        context["can_create_service_order"] = user_can_create_service_order(self.request)
        return context


class ClientServiceOrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "client_portal/service_order_detail.html"
    context_object_name = "order"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return allowed_service_orders(self.request)

    def get_object(self, queryset=None):
        order = ServiceOrder.objects.select_related("client", "operational_site", "asset").filter(pk=self.kwargs["pk"]).first()
        if not order or not user_can_access_service_order(self.request, order):
            raise Http404("Chamado não encontrado.")
        return order

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_logs = WorkLog.objects.filter(service_order=self.object).order_by("-started_at", "-created_at")
        context["client_history"] = [
            {"occurred_at": log.started_at or log.created_at, "label": "Atendimento tecnico registrado"}
            for log in work_logs
        ]
        context["next_portal_visit"] = get_service_order_portal_visit(self.request, self.object)
        context["can_create_service_order"] = user_can_create_service_order(self.request)
        return context


class ClientAssetListView(LoginRequiredMixin, ListView):
    template_name = "client_portal/asset_list.html"
    context_object_name = "assets"
    paginate_by = 25

    def get_queryset(self):
        return allowed_assets(self.request).order_by("operational_site__name", "asset_tag").annotate(
            open_orders_count=Count(
                "service_orders",
                filter=Q(service_orders__status__in=(ServiceOrder.Status.OPEN, *IN_PROGRESS_STATUSES)),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create_service_order"] = user_can_create_service_order(self.request)
        return context


class TechnicalPortalHomeView(ClientPortalDashboardView):
    pass


class TechnicalPortalSearchView(LoginRequiredMixin, TemplateView):
    template_name = "technical_portal/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        articles = TechnicalArticle.objects.none()
        error_codes = ErrorCode.objects.none()

        if query:
            articles = TechnicalArticle.objects.select_related("category").filter(
                Q(title__icontains=query) | Q(summary__icontains=query) | Q(content__icontains=query) | Q(tags__icontains=query),
                is_active=True,
                category__is_active=True,
            )
            error_codes = ErrorCode.objects.select_related("category").filter(
                Q(code__icontains=query)
                | Q(title__icontains=query)
                | Q(brand__icontains=query)
                | Q(model__icontains=query)
                | Q(probable_cause__icontains=query)
                | Q(recommended_action__icontains=query)
                | Q(equipment_type__icontains=query),
                is_active=True,
                category__is_active=True,
            )

        context["query"] = query
        context["articles"] = articles
        context["error_codes"] = error_codes
        context["result_count"] = articles.count() + error_codes.count()
        context["can_create_service_order"] = user_can_create_service_order(self.request)
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
        context["articles"] = self.object.articles.filter(is_active=True)
        context["error_codes"] = self.object.error_codes.filter(is_active=True)
        context["can_create_service_order"] = user_can_create_service_order(self.request)
        return context
