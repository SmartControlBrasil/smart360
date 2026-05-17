from django.db.models import Case, IntegerField, Q, Value, When

from ..models import SearchBoostRule, SearchIndexEntry, SearchQueryLog, SearchSynonym


class SearchIndexService:
    @staticmethod
    def upsert_entry(**validated_data):
        entry, _ = SearchIndexEntry.objects.update_or_create(
            source_module=validated_data["source_module"],
            item_type=validated_data["item_type"],
            item_id=validated_data["item_id"],
            defaults=validated_data,
        )
        return entry


class SearchQueryService:
    @staticmethod
    def expand_query(query_text):
        tokens = [token.strip() for token in query_text.split() if token.strip()]
        synonyms = []
        synonym_rows = SearchSynonym.objects.filter(term__in=tokens, is_active=True).values_list("synonym", flat=True)
        synonyms.extend(synonym_rows)
        return list(dict.fromkeys(tokens + synonyms))

    @staticmethod
    def apply_filters(*, queryset, params):
        if params.get("source_module"):
            queryset = queryset.filter(source_module=params["source_module"])
        if params.get("item_type"):
            queryset = queryset.filter(item_type=params["item_type"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("category"):
            queryset = queryset.filter(category=params["category"])
        return queryset

    @staticmethod
    def apply_boosts(*, queryset):
        boosts = SearchBoostRule.objects.filter(is_active=True)
        conditions = []
        for rule in boosts:
            condition = Q()
            if rule.source_module:
                condition &= Q(source_module=rule.source_module)
            if rule.item_type:
                condition &= Q(item_type=rule.item_type)
            if rule.status:
                condition &= Q(status=rule.status)
            conditions.append(When(condition, then=Value(rule.boost_value)))
        if not conditions:
            return queryset.annotate(boost_score=Value(0, output_field=IntegerField()))
        return queryset.annotate(
            boost_score=Case(
                *conditions,
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    @staticmethod
    def search(*, user, query_text, filters):
        expanded_terms = SearchQueryService.expand_query(query_text=query_text)
        queryset = SearchIndexEntry.objects.filter(is_active=True)

        if expanded_terms:
            query = Q()
            for term in expanded_terms:
                query |= Q(title__icontains=term)
                query |= Q(subtitle__icontains=term)
                query |= Q(body_text__icontains=term)
                query |= Q(search_text__icontains=term)
            queryset = queryset.filter(query)

        queryset = SearchQueryService.apply_filters(queryset=queryset, params=filters)
        queryset = SearchQueryService.apply_boosts(queryset=queryset)

        ordering = filters.get("ordering") or "-boost_score"
        if ordering == "title":
            queryset = queryset.order_by("title")
        elif ordering == "updated_at":
            queryset = queryset.order_by("-updated_at")
        else:
            queryset = queryset.order_by("-boost_score", "-updated_at", "title")

        SearchQueryLog.objects.create(
            query_text=query_text,
            performed_by=user if user and user.is_authenticated else None,
            source_context=filters.get("source_context", ""),
            filters_json=filters,
            results_count=queryset.count(),
        )
        return queryset

    @staticmethod
    def autocomplete(*, query_text):
        queryset = SearchIndexEntry.objects.filter(is_active=True)
        if query_text:
            queryset = queryset.filter(Q(title__icontains=query_text) | Q(search_text__icontains=query_text))
        return queryset.order_by("title")[:10]

