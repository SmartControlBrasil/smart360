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
        "waiterbot",
        "garcom",
        "restaurante",
        "carebot",
        "saude",
        "clinica",
        "hostbot",
        "recepcao",
        "eventos",
        "mowerbot",
        "grama",
        "jardim",
    }
    CLEANING_INTENT_TERMS = {
        "limpeza",
        "hygibot",
        "hygi",
        "dune",
        "duno",
        "dunobot",
    }
    BUDDY_INTENT_TERMS = {
        "buddy",
        "budy",
        "cao",
        "cachorro",
        "quadrupede",
    }
    LIRO_INTENT_TERMS = {"liro", "little", "littlebot", "educacional", "escola", "creche", "infantil"}
    WAITER_INTENT_TERMS = {"waiter", "waiterbot", "garcom", "restaurante", "bandeja", "food"}
    CARE_INTENT_TERMS = {"carebot", "saude", "clinica", "idoso", "idosos", "telemedicina", "teleatendimento"}
    HOST_INTENT_TERMS = {"hostbot", "host", "recepcao", "recepcionista", "evento", "eventos", "visitante"}
    MOWER_INTENT_TERMS = {"mowerbot", "mower", "grama", "jardim", "talude", "cortador"}
    ORBIT_INTENT_TERMS = {"orbit", "orbitbot", "patrol", "seguranca", "patrulha", "ronda", "vigilancia"}
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
        score = 0

        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", searchable):
                score += 12
            elif term in searchable:
                score += 5

        slug = item.slug or ""
        if score > 0:
            score += max(1, item.priority // 20)

        is_xyron_overview_query = self._is_xyron_overview_query(normalized_query, terms)
        if has_xyron_intent:
            if slug.startswith("xyron-"):
                score += 22
            elif slug == "xyron-robotics-visao-geral":
                score += 18
            else:
                score -= 4
        if is_xyron_overview_query:
            if slug == "xyron-robotics-visao-geral":
                score += 75
            elif slug.startswith("xyron-"):
                score -= 12

        if "pmoc" in terms and slug == "pmoc":
            score += 35

        buddy_terms = self.BUDDY_INTENT_TERMS
        cleaning_terms = self.CLEANING_INTENT_TERMS

        if terms and buddy_terms.intersection(terms) and slug == "xyron-buddy-bot":
            score += 60
        liro_specific_terms = {"apae", "neurodivergente", "neurodivergencia", "autismo", "tea", "tdah", "inclusao", "multidisciplinar"}
        liro_plan_terms = {"plano", "aula", "pedagogico", "pedagogica", "bncc", "infantil", "fundamental", "medio", "historia", "quiz"}
        if self.LIRO_INTENT_TERMS.intersection(terms) and slug == "xyron-liro-littlebot":
            score += 58
        if liro_specific_terms.intersection(terms) and slug == "xyron-liro-apae-clinicas":
            score += 150
        if liro_plan_terms.intersection(terms) and slug == "xyron-liro-planos-aula-pedagogico":
            score += 150
        if (liro_specific_terms.intersection(terms) or liro_plan_terms.intersection(terms)) and slug == "xyron-liro-littlebot":
            score -= 80
        if {"neo", "neobot", "nebot"}.intersection(terms) and slug == "xyron-neo-bot":
            score += 55
        if {"neo", "neobot", "nebot"}.intersection(terms) and slug == "xyron-hostbot":
            score -= 30
        if self.ORBIT_INTENT_TERMS.intersection(terms) and slug == "xyron-orbit-patrol-bot":
            score += 95
        if self.ORBIT_INTENT_TERMS.intersection(terms) and slug == "xyron-robotics-visao-geral":
            score -= 50
        if cleaning_terms.intersection(terms) and slug == "xyron-hygibot-dune-bot":
            score += 55
        if self.WAITER_INTENT_TERMS.intersection(terms) and slug == "xyron-waiterbot":
            score += 55
        if self.CARE_INTENT_TERMS.intersection(terms) and slug == "xyron-carebot":
            score += 95
        if self.CARE_INTENT_TERMS.intersection(terms) and slug.startswith("xyron-liro-") and not {"liro", "littlebot", "apae"}.intersection(terms):
            score -= 70
        if self.HOST_INTENT_TERMS.intersection(terms) and slug == "xyron-hostbot":
            score += 55
        if self.MOWER_INTENT_TERMS.intersection(terms) and slug == "xyron-mowerbot":
            score += 55
        if cleaning_terms.intersection(terms) and slug == "xyron-hygibot-dune-bot" and "robo" in terms:
            score += 20

        # Quando a intenção atual é claramente limpeza, priorizamos o HygiBot
        # e penalizamos Buddy, a menos que haja menção explícita ao Buddy/cão.
        if cleaning_terms.intersection(terms) and not buddy_terms.intersection(terms):
            if slug == "xyron-buddy-bot":
                score -= 45
            if slug == "xyron-hygibot-dune-bot":
                score += 35

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
        if "nebot" in normalized_query:
            expansions.append("neobot neo bot robo de recepcao")
        if "neo bot" in normalized_query or "neo-bot" in normalized_query:
            expansions.append("neobot neo robo de recepcao")
        if "robo neo" in normalized_query:
            expansions.append("neobot neo bot robo de recepcao")
        if "neobot" in normalized_query:
            expansions.append("neo bot robo de recepcao")
        if "robo educacional" in normalized_query or "robo para escola" in normalized_query or "robô para escola" in normalized_query:
            expansions.append("liro littlebot robo educacional escola professor")
        if "garcom" in normalized_query or "garçom" in normalized_query or "restaurante" in normalized_query:
            expansions.append("waiterbot waiter bot robo garcom restaurante bandeja entrega")
        if "saude" in normalized_query or "clínica" in normalized_query or "clinica" in normalized_query or "idoso" in normalized_query:
            expansions.append("carebot care bot robo saude clinica teleatendimento cuidado")
        if "recepcao" in normalized_query or "recepção" in normalized_query or "evento" in normalized_query:
            expansions.append("hostbot host bot neobot robo recepcao eventos visitantes")
        if "grama" in normalized_query or "jardim" in normalized_query or "talude" in normalized_query:
            expansions.append("mowerbot mower bot robo cortador grama jardim talude")
        if "ronda" in normalized_query or "patrulha" in normalized_query or "seguranca" in normalized_query or "segurança" in normalized_query:
            expansions.append("orbitbot orbit patrol bot robo seguranca patrulha ronda")
        if "duno" in normalized_query or "dune" in normalized_query:
            expansions.append("hygibot hygi bot robo de limpeza")
        if "hygbot" in normalized_query or "higibot" in normalized_query:
            expansions.append("hygibot hygi bot robo de limpeza")
        if "hygi " in normalized_query or normalized_query.endswith("hygi") or " higi" in normalized_query:
            expansions.append("hygibot hygi bot")
        if "lttle" in normalized_query or "litlle" in normalized_query or "litle" in normalized_query:
            expansions.append("little littlebot liro robo educacional")
        if "connect bot" in normalized_query or "conectbot" in normalized_query:
            expansions.append("connectbot")
        return " ".join(expansions)

    def _is_xyron_overview_query(self, normalized_query: str, terms: list[str]) -> bool:
        if "xyron" not in terms:
            return False
        query = f" {normalized_query.strip()} "
        overview_patterns = (
            " o que e a xyron ",
            " o que e xyron ",
            " quem e a xyron ",
            " quem e xyron ",
            " empresa xyron ",
        )
        if any(pattern in query for pattern in overview_patterns):
            return True
        # Query curta apenas com a marca.
        return len(terms) <= 2 and "xyron" in terms
