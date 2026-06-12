import re
import unicodedata
from pathlib import Path

from .file_audit import human_readable_size


POSITIVE_TERMS = {
    "fmea": 14,
    "falha": 10,
    "falhas": 10,
    "confiabilidade": 12,
    "disponibilidade": 11,
    "manutencao": 10,
    "tpm": 12,
    "kaizen": 10,
    "preventiva": 8,
    "preditiva": 9,
    "autonoma": 8,
    "planejada": 8,
    "robotica": 10,
    "automacao": 10,
    "controle": 7,
    "clp": 10,
    "sensor": 8,
    "sensores": 8,
    "instrumentacao": 9,
    "inteligencia artificial": 11,
    "ia": 8,
    "dados": 6,
    "diagnostico": 9,
}
NEGATIVE_TERMS = {
    "direito": -12,
    "economia": -10,
    "legislacao": -12,
    "juridico": -12,
    "marketing": -7,
    "web analytics": -8,
    "calculo numerico": -5,
}


def normalize_search_text(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def score_pdf_candidate(path, size_bytes):
    normalized = normalize_search_text(path)
    matched_terms = []
    score = 0
    for term, points in POSITIVE_TERMS.items():
        if _contains_term(normalized, term):
            matched_terms.append(term)
            score += points
    negative_matches = []
    for term, points in NEGATIVE_TERMS.items():
        if _contains_term(normalized, term):
            negative_matches.append(term)
            score += points

    size_mb = size_bytes / (1024 * 1024)
    if size_mb <= 2:
        score += 3
    elif size_mb <= 10:
        score += 1
    elif size_mb > 20:
        score -= 20

    notes = []
    if negative_matches:
        notes.append(f"lower priority: {', '.join(negative_matches)}")
    if size_mb > 20:
        notes.append("too large for current selection")
    return {
        "score": score,
        "matched_terms": matched_terms,
        "recommended_category": _recommended_category(normalized, matched_terms),
        "notes": "; ".join(notes),
    }


def select_pdf_candidates(base_path, max_size_mb=20, limit=50):
    base_path = Path(base_path)
    max_size_bytes = max_size_mb * 1024 * 1024
    candidates = []
    oversized = []
    total_pdfs = 0
    if not base_path.exists():
        return _selection_result(base_path, total_pdfs, candidates, oversized, max_size_mb)

    for path in sorted(item for item in base_path.rglob("*") if item.is_file() and item.suffix.lower() == ".pdf"):
        total_pdfs += 1
        size_bytes = path.stat().st_size
        relative_path = path.relative_to(base_path).as_posix()
        scored = score_pdf_candidate(relative_path, size_bytes)
        item = {
            "relative_path": relative_path,
            "filename": path.name,
            "size_bytes": size_bytes,
            "size_human": human_readable_size(size_bytes),
            **scored,
        }
        if size_bytes > max_size_bytes:
            if "too large for current selection" not in item["notes"]:
                item["notes"] = "; ".join(filter(None, [item["notes"], "too large for current selection"]))
            oversized.append(item)
        elif item["score"] > 0 and item["matched_terms"]:
            candidates.append(item)

    candidates.sort(key=lambda item: (-item["score"], item["size_bytes"], item["relative_path"]))
    oversized.sort(key=lambda item: (-item["size_bytes"], item["relative_path"]))
    return _selection_result(base_path, total_pdfs, candidates[:limit], oversized, max_size_mb)


def _contains_term(normalized, term):
    return re.search(rf"(?:^|\s){re.escape(term)}(?:$|\s)", normalized) is not None


def _recommended_category(normalized, matched_terms):
    matched = set(matched_terms)
    if matched.intersection({"fmea", "falha", "falhas", "confiabilidade", "disponibilidade", "manutencao", "tpm", "kaizen", "preventiva", "preditiva", "autonoma", "planejada"}):
        return "manutencao"
    if matched.intersection({"inteligencia artificial", "ia", "dados"}):
        return "ia_aplicada"
    if matched.intersection({"robotica", "automacao", "controle", "clp", "sensor", "sensores", "instrumentacao", "diagnostico"}):
        return "engenharia"
    if "engenharia" in normalized:
        return "engenharia"
    return "academico"


def _selection_result(base_path, total_pdfs, candidates, oversized, max_size_mb):
    return {
        "base_path": str(Path(base_path).resolve()),
        "max_size_mb": max_size_mb,
        "total_pdfs": total_pdfs,
        "candidate_count": len(candidates),
        "oversized_count": len(oversized),
        "candidates": candidates,
        "oversized": oversized,
    }
