from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import SearchBoostRule, SearchIndexEntry, SearchQueryLog, SearchSavedFilter, SearchSynonym
from ..services.search_service import SearchQueryService
from .serializers import (
    SearchBoostRuleSerializer,
    SearchIndexEntrySerializer,
    SearchQueryLogSerializer,
    SearchSavedFilterSerializer,
    SearchSynonymSerializer,
)


class SearchBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class SearchIndexEntryViewSet(SearchBaseViewSet):
    queryset = SearchIndexEntry.objects.all()
    serializer_class = SearchIndexEntrySerializer
    filterset_fields = ("source_module", "item_type", "status", "category", "is_active")
    search_fields = ("title", "subtitle", "body_text", "search_text", "item_id", "url_path")
    ordering_fields = ("updated_at", "created_at", "title")


class SearchQueryLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchQueryLog.objects.select_related("performed_by").all()
    serializer_class = SearchQueryLogSerializer
    filterset_fields = ("performed_by", "source_context")
    search_fields = ("query_text", "performed_by__email")
    ordering_fields = ("executed_at", "created_at")


class SearchSavedFilterViewSet(SearchBaseViewSet):
    queryset = SearchSavedFilter.objects.select_related("owner_user", "owner_company").all()
    serializer_class = SearchSavedFilterSerializer
    filterset_fields = ("owner_user", "owner_company", "is_active")
    search_fields = ("name", "slug")
    ordering_fields = ("name", "created_at", "updated_at")


class SearchSynonymViewSet(SearchBaseViewSet):
    queryset = SearchSynonym.objects.all()
    serializer_class = SearchSynonymSerializer
    filterset_fields = ("is_active",)
    search_fields = ("term", "synonym")
    ordering_fields = ("term", "created_at", "updated_at")


class SearchBoostRuleViewSet(SearchBaseViewSet):
    queryset = SearchBoostRule.objects.all()
    serializer_class = SearchBoostRuleSerializer
    filterset_fields = ("source_module", "item_type", "status", "is_active")
    search_fields = ("source_module", "item_type", "status")
    ordering_fields = ("boost_value", "created_at", "updated_at")


class GlobalSearchQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query_text = request.query_params.get("q", "").strip()
        filters = {
            "source_module": request.query_params.get("source_module", "").strip(),
            "item_type": request.query_params.get("item_type", "").strip(),
            "status": request.query_params.get("status", "").strip(),
            "category": request.query_params.get("category", "").strip(),
            "ordering": request.query_params.get("ordering", "").strip(),
            "source_context": request.query_params.get("source_context", "").strip(),
        }
        queryset = SearchQueryService.search(user=request.user, query_text=query_text, filters=filters)
        serializer = SearchIndexEntrySerializer(queryset[:50], many=True)
        return Response({"count": queryset.count(), "results": serializer.data}, status=status.HTTP_200_OK)


class GlobalSearchAutocompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query_text = request.query_params.get("q", "").strip()
        queryset = SearchQueryService.autocomplete(query_text=query_text)
        serializer = SearchIndexEntrySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

