from rest_framework import serializers

from ..models import SearchBoostRule, SearchIndexEntry, SearchQueryLog, SearchSavedFilter, SearchSynonym
from ..services.search_service import SearchIndexService


class SearchIndexEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchIndexEntry
        fields = (
            "id",
            "public_id",
            "source_module",
            "item_type",
            "item_id",
            "title",
            "subtitle",
            "body_text",
            "search_text",
            "status",
            "category",
            "url_path",
            "metadata",
            "is_active",
            "updated_at",
            "created_at",
        )
        read_only_fields = ("id", "public_id", "updated_at", "created_at")

    def create(self, validated_data):
        return SearchIndexService.upsert_entry(**validated_data)


class SearchQueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQueryLog
        fields = ("id", "public_id", "query_text", "performed_by", "source_context", "filters_json", "results_count", "executed_at", "created_at")
        read_only_fields = fields


class SearchSavedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchSavedFilter
        fields = ("id", "public_id", "name", "slug", "owner_user", "owner_company", "filter_config", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class SearchSynonymSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchSynonym
        fields = ("id", "public_id", "term", "synonym", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class SearchBoostRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchBoostRule
        fields = ("id", "public_id", "source_module", "item_type", "status", "boost_value", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

