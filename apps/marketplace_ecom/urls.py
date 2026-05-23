from django.urls import path

from .views import MarketplaceHomeView, MarketplaceQuoteRequestView, ProductDetailView, ProductListView

app_name = "marketplace_ecom"

urlpatterns = [
    path("", MarketplaceHomeView.as_view(), name="home"),
    path("products/", ProductListView.as_view(), name="products"),
    path("products/<slug:slug>/request-quote/", MarketplaceQuoteRequestView.as_view(), name="request-quote"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]
