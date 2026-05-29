from django.urls import path

from .views import (
    ClientAssetListView,
    ClientPortalDashboardView,
    ClientServiceOrderCreateView,
    ClientServiceOrderDetailView,
    ClientServiceOrderListView,
    TechnicalCategoryDetailView,
    TechnicalPortalSearchView,
)

app_name = "technical_portal"

urlpatterns = [
    path("", ClientPortalDashboardView.as_view(), name="home"),
    path("chamados/", ClientServiceOrderListView.as_view(), name="service-orders"),
    path("chamados/novo/", ClientServiceOrderCreateView.as_view(), name="service-order-create"),
    path("chamados/<int:pk>/", ClientServiceOrderDetailView.as_view(), name="service-order-detail"),
    path("equipamentos/", ClientAssetListView.as_view(), name="assets"),
    path("search/", TechnicalPortalSearchView.as_view(), name="search"),
    path("category/<slug:slug>/", TechnicalCategoryDetailView.as_view(), name="category-detail"),
]
