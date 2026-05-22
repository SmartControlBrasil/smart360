from django.urls import path

from .views import (
    TechnicalCategoryDetailView,
    TechnicalPortalHomeView,
    TechnicalPortalSearchView,
)

app_name = "technical_portal"

urlpatterns = [
    path("", TechnicalPortalHomeView.as_view(), name="home"),
    path("search/", TechnicalPortalSearchView.as_view(), name="search"),
    path("category/<slug:slug>/", TechnicalCategoryDetailView.as_view(), name="category-detail"),
]
