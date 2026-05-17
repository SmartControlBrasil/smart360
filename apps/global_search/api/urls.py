from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    GlobalSearchAutocompleteView,
    GlobalSearchQueryView,
    SearchBoostRuleViewSet,
    SearchIndexEntryViewSet,
    SearchQueryLogViewSet,
    SearchSavedFilterViewSet,
    SearchSynonymViewSet,
)

router = DefaultRouter()
router.register("index-entries", SearchIndexEntryViewSet, basename="search-index-entries")
router.register("query-logs", SearchQueryLogViewSet, basename="search-query-logs")
router.register("saved-filters", SearchSavedFilterViewSet, basename="search-saved-filters")
router.register("synonyms", SearchSynonymViewSet, basename="search-synonyms")
router.register("boost-rules", SearchBoostRuleViewSet, basename="search-boost-rules")

urlpatterns = router.urls + [
    path("query/", GlobalSearchQueryView.as_view(), name="search-query"),
    path("autocomplete/", GlobalSearchAutocompleteView.as_view(), name="search-autocomplete"),
]

