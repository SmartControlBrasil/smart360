import re


def split_text_into_chunks(text, max_chars=1200, overlap_chars=150):
    text = (text or "").strip()
    if not text:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    overlap_chars = max(0, min(overlap_chars, max_chars // 2))

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    units = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", paragraph) if part.strip()]
        for sentence in sentences:
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(
                    sentence[start : start + max_chars].strip()
                    for start in range(0, len(sentence), max_chars)
                    if sentence[start : start + max_chars].strip()
                )

    chunks = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            overlap = current[-overlap_chars:].strip() if overlap_chars else ""
            current = f"{overlap}\n\n{unit}".strip() if overlap else unit
            if len(current) > max_chars:
                chunks.append(current[:max_chars].strip())
                current = current[max_chars - overlap_chars :].strip()
        else:
            chunks.append(unit[:max_chars].strip())
            current = unit[max_chars - overlap_chars :].strip()

    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]
