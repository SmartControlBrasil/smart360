import re

from django.db.models import Q

from .models import LiviaKnowledgeItem


class LiviaKnowledgeService:
    max_context_chars = 1800

    def search(self, query: str, limit: int = 5):
        queryset = LiviaKnowledgeItem.objects.filter(is_active=True)
        terms = self._terms(query)
        if not terms:
            return list(queryset.order_by("-priority", "title")[:limit])

        filters = Q()
        for term in terms:
            filters |= Q(title__icontains=term) | Q(content__icontains=term) | Q(keywords__icontains=term)

        return list(queryset.filter(filters).distinct().order_by("-priority", "title")[:limit])

    def build_context(self, query: str, limit: int = 5) -> str:
        items = self.search(query, limit=limit)
        if not items:
            return ""

        chunks = []
        remaining = self.max_context_chars
        for item in items:
            content = " ".join(item.content.split())
            line = f"- {item.title} ({item.get_category_display()}): {content}"
            if len(line) > remaining:
                line = line[: max(0, remaining - 3)].rstrip() + "..."
            if line.strip("."):
                chunks.append(line)
                remaining -= len(line) + 1
            if remaining <= 0:
                break

        if not chunks:
            return ""
        return "Base de conhecimento da Smart Control Brasil:\n" + "\n".join(chunks)

    def _terms(self, query: str):
        normalized = (query or "").lower()
        return [term for term in re.findall(r"[\wÀ-ÿ-]{3,}", normalized)[:12]]
