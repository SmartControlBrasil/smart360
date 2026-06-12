import re
import unicodedata

from apps.livia_assistant.models import LiviaKnowledgeChunk


STOPWORDS = {"a", "ao", "com", "da", "de", "do", "e", "em", "o", "os", "para", "por", "que", "um", "uma"}
ALIASES = {
    "recepcionista": {"recepcao", "interativo", "neobot", "hostbot"},
    "limpeza": {"duno", "dunobot", "hygibot", "higienizacao"},
    "supermercado": {"supermercados"},
    "robo": {"robotica"},
}


def _normalize(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _terms(text):
    terms = {term for term in re.findall(r"[a-z0-9-]{3,}", _normalize(text)) if term not in STOPWORDS}
    for term in tuple(terms):
        terms.update(ALIASES.get(term, set()))
    return terms


def retrieve_livia_context(question, limit=5):
    query_terms = _terms(question)
    if not query_terms:
        return []

    results = []
    chunks = LiviaKnowledgeChunk.objects.select_related("document").filter(is_active=True, document__is_active=True)
    for chunk in chunks:
        document = chunk.document
        fields = {
            "content": _normalize(chunk.content),
            "title": _normalize(document.title),
            "category": _normalize(document.category),
            "product": _normalize(document.product),
            "application": _normalize(document.application),
        }
        score = 0
        for term in query_terms:
            score += fields["content"].count(term) * 3
            score += fields["title"].count(term) * 5
            score += fields["category"].count(term) * 4
            score += fields["application"].count(term) * 5
            score += fields["product"].count(term) * 8
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
        })

    results.sort(key=lambda item: (item["score"], -item["chunk"].chunk_index), reverse=True)
    return results[:limit]
