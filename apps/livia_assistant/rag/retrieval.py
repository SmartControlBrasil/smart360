import re
import unicodedata
from collections import Counter

from apps.livia_assistant.models import LiviaKnowledgeChunk


STOPWORDS = {"ajuda", "aos", "como", "com", "da", "das", "de", "do", "dos", "e", "em", "esse", "essa", "explicar", "o", "os", "para", "por", "que", "reduzir", "serve", "um", "uma", "usar"}
ALIASES = {
    "recepcionista": {"recepcao", "interativo", "neobot", "hostbot"},
    "limpeza": {"duno", "dunobot", "hygibot", "higienizacao"},
    "supermercado": {"supermercados"},
    "robo": {"robotica"},
    "parada": {"paradas", "disponibilidade", "falha", "falhas"},
    "paradas": {"parada", "disponibilidade", "falha", "falhas"},
    "fmea": {"falha", "falhas", "causa", "risco"},
    "tpm": {"manutencao", "disponibilidade", "falha", "falhas"},
}
MAINTENANCE_TERMS = {"tpm", "manutencao", "falha", "falhas", "confiabilidade", "disponibilidade", "parada", "paradas", "fmea", "fmeca", "preventiva", "preditiva", "planejada", "autonoma", "mtbf", "mttr", "rca", "causa raiz"}
MAINTENANCE_AFFINITY_TERMS = MAINTENANCE_TERMS - {"parada", "paradas"}
AUTOMATION_TERMS = {"automacao", "clp", "ihm", "sensores", "sensor", "inversor", "servo", "instrumentacao", "controle", "processo industrial"}
ROBOTICS_TERMS = {"robo", "robotica"}
XYRON_TERMS = {"xyron", "liro", "duno", "dunobot", "hygi", "hygibot", "neobot", "hostbot", "buddy", "orbit", "orbitbot", "patrol"}
COMMERCIAL_TERMS = {"orcamento", "proposta", "preco", "comprar", "demonstracao", "contato", "whatsapp", "prazo", "estoque"}
GENERIC_MARKERS = {"guia de estudos", "guia_de_estudos", "modulo", "edicao de videos", "premiere", "animate", "curso generico"}


def detect_question_intent(question):
    normalized = _normalize(question)
    terms = _terms(question)
    if terms.intersection(XYRON_TERMS):
        return "produto_xyron"
    if terms.intersection(ROBOTICS_TERMS):
        return "robotica"
    if _has_any(normalized, MAINTENANCE_TERMS):
        return "manutencao"
    if _has_any(normalized, AUTOMATION_TERMS):
        return "automacao"
    if _has_any(normalized, COMMERCIAL_TERMS):
        return "comercial"
    return "generico"


def retrieve_livia_context(question, limit=5):
    query_terms = _terms(question)
    if not query_terms:
        return []
    intent = detect_question_intent(question)

    results = []
    chunks = LiviaKnowledgeChunk.objects.select_related("document").filter(is_active=True, document__is_active=True)
    for chunk in chunks:
        document = chunk.document
        source_path = str(document.source_path or "")
        fields = {
            "content": _normalize(chunk.content),
            "title": _normalize(document.title),
            "category": _normalize(document.category),
            "product": _normalize(document.product),
            "application": _normalize(document.application),
            "source_path": _normalize(source_path),
        }
        score = _text_score(query_terms, fields)
        score += _intent_score(intent, fields)
        score += _generic_penalty(fields)
        if score <= 0:
            continue
        results.append({
            "content": chunk.content,
            "document_title": document.title,
            "category": document.category,
            "product": document.product,
            "application": document.application,
            "score": score,
            "metadata": {**document.metadata, **chunk.metadata},
            "chunk": chunk,
            "source_path": source_path,
        })

    results.sort(key=lambda item: (item["score"], -item["chunk"].chunk_index), reverse=True)
    return _diverse_results(results, limit)


def _text_score(query_terms, fields):
    score = 0
    for term in query_terms:
        score += min(fields["content"].count(term), 8) * 3
        score += min(fields["title"].count(term), 3) * 6
        score += min(fields["category"].count(term), 2) * 5
        score += min(fields["application"].count(term), 2) * 5
        score += min(fields["product"].count(term), 2) * 9
    return score


def _intent_score(intent, fields):
    category = fields["category"]
    corpus = " ".join(fields.values())
    if intent == "manutencao":
        if category == "manutencao":
            return 45
        if category == "smart_control" and _has_any(corpus, MAINTENANCE_TERMS | AUTOMATION_TERMS | {"diagnostico"}):
            return 16
        if category == "academico":
            return 5 if _has_any(corpus, MAINTENANCE_AFFINITY_TERMS) else -35
        if category == "engenharia":
            return 8 if _has_any(corpus, MAINTENANCE_AFFINITY_TERMS) else -30
        return -12
    if intent == "automacao":
        if category in {"engenharia", "smart_control"}:
            return 32
        if category == "academico" and not _has_any(corpus, AUTOMATION_TERMS):
            return -30
        return -8
    if intent in {"robotica", "produto_xyron"}:
        if category in {"robotica", "xyron", "aplicacoes"}:
            return 38
        if category in {"academico", "manutencao"} and not _has_any(corpus, ROBOTICS_TERMS | XYRON_TERMS):
            return -35
        return -10
    if intent == "comercial":
        return 25 if category in {"comercial", "smart_control"} else -5
    return 0


def _generic_penalty(fields):
    title_and_path = f"{fields['title']} {fields['source_path']}"
    return -45 if any(marker in title_and_path for marker in GENERIC_MARKERS) else 0


def _diverse_results(results, limit):
    selected = []
    counts = Counter()
    for max_per_document in (1, 2):
        for result in results:
            key = result["source_path"] or result["document_title"]
            if counts[key] >= max_per_document or result in selected:
                continue
            selected.append(result)
            counts[key] += 1
            if len(selected) >= limit:
                return selected
    return selected


def _terms(text):
    terms = {term for term in re.findall(r"[a-z0-9-]{2,}", _normalize(text)) if term not in STOPWORDS}
    for term in tuple(terms):
        terms.update(ALIASES.get(term, set()))
    return terms


def _normalize(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _has_any(text, terms):
    return any(re.search(rf"(?:^|\W){re.escape(term)}(?:$|\W)", text) for term in terms)
