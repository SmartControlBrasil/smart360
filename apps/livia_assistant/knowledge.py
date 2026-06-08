import re
import unicodedata

from django.db.models import Q

from .models import LiviaKnowledgeItem


class LiviaKnowledgeService:
    max_context_chars = 1800
    min_relevance_score = 8

    XYRON_INTENT_TERMS = {
        "robo",
        "robot",
        "bot",
        "xyron",
        "liro",
        "littlebot",
        "buddy",
        "budy",
        "neo",
        "orbit",
        "patrol",
        "dune",
        "duno",
        "hygibot",
        "waiter",
        "carebot",
        "hostbot",
        "mowerbot",
    }
    STOPWORDS = {
        "que",
        "para",
        "com",
        "sobre",
        "tem",
        "uma",
        "uns",
        "das",
        "dos",
        "de",
        "da",
        "do",
        "o",
        "a",
        "e",
    }

    def search(self, query: str, limit: int = 5):
        scored_items = self._search_with_scores(query)
        return [item for item, _score in scored_items[:limit]]

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

    def _search_with_scores(self, query: str):
        queryset = LiviaKnowledgeItem.objects.filter(is_active=True)
        normalized_query = self._normalize(query)
        terms = self._terms(normalized_query)
        if not terms:
            return []

        filters = Q()
        for term in terms:
            filters |= Q(title__icontains=term) | Q(content__icontains=term) | Q(keywords__icontains=term)

        # Traz candidatos por texto bruto e depois ranqueia com normalização sem acentos.
        candidates = list(queryset.filter(filters).distinct())
        # Quando o filtro textual bruto falha por acentuação/sinônimos, ainda ranqueamos
        # toda a base ativa com normalização para evitar quedas indevidas em fallback.
        if not candidates:
            candidates = list(queryset)

        has_xyron_intent = any(term in self.XYRON_INTENT_TERMS for term in terms)
        scored = []
        for item in candidates:
            score = self._score_item(item, normalized_query, terms, has_xyron_intent)
            if score >= self.min_relevance_score:
                scored.append((item, score))

        scored.sort(key=lambda pair: (pair[1], pair[0].priority), reverse=True)
        return scored

    def _score_item(self, item: LiviaKnowledgeItem, normalized_query: str, terms: list[str], has_xyron_intent: bool) -> int:
        searchable = self._normalize(f"{item.title} {item.keywords} {item.content}")
        score = max(1, item.priority // 10)

        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", searchable):
                score += 12
            elif term in searchable:
                score += 5

        slug = item.slug or ""
        if has_xyron_intent:
            if slug.startswith("xyron-"):
                score += 22
            elif slug == "xyron-robotics-visao-geral":
                score += 18
            else:
                score -= 4

        if "pmoc" in terms and slug == "pmoc":
            score += 35

        buddy_terms = {"buddy", "budy", "cao", "cachorro", "quadrupede", "robo", "robotico"}
        if terms and buddy_terms.intersection(terms) and slug == "xyron-buddy-bot":
            score += 60
        if {"neo", "neobot"}.intersection(terms) and slug == "xyron-neo-bot":
            score += 55
        if {"orbit", "patrol"}.intersection(terms) and slug == "xyron-orbit-patrol-bot":
            score += 55
        if {"hygibot", "dune", "duno", "dunobot"}.intersection(terms) and slug == "xyron-hygibot-dune-bot":
            score += 55

        return score

    def _terms(self, query: str):
        expanded_query = self._expand_aliases(query or "")
        tokens = re.findall(r"[a-z0-9-]{2,}", expanded_query)
        unique_terms = []
        for token in tokens:
            if token in self.STOPWORDS:
                continue
            if len(token) == 2 and token not in {"os", "clp"}:
                continue
            if token not in unique_terms:
                unique_terms.append(token)
            if len(unique_terms) >= 16:
                break
        return unique_terms

    def _normalize(self, text: str) -> str:
        text = (text or "").lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return text

    def _expand_aliases(self, query: str) -> str:
        normalized_query = self._normalize(query)
        expansions = [normalized_query]
        if "cao robo" in normalized_query or "cachorro robo" in normalized_query or "robo cachorro" in normalized_query:
            expansions.append("buddy budy buddy bot robo quadrupede")
        if "budy" in normalized_query:
            expansions.append("buddy buddy bot robo quadrupede")
        if "neobot" in normalized_query:
            expansions.append("neo bot robo de recepcao")
        if "duno" in normalized_query or "dune" in normalized_query:
            expansions.append("hygibot hygi bot robo de limpeza")
        return " ".join(expansions)
