from .retrieval import retrieve_livia_context


def build_context_for_prompt(question, limit=5, max_chars=4000):
    results = retrieve_livia_context(question, limit=limit)
    if not results:
        return ""

    sections = []
    seen = set()
    remaining = max_chars
    for result in results:
        content = " ".join(result["content"].split())
        if content in seen:
            continue
        seen.add(content)
        lines = [
            f"[DOCUMENTO: {result['document_title']}]",
            f"Categoria: {result['category']}" if result["category"] else "",
            f"Produto: {result['product']}" if result["product"] else "",
            f"Aplicação: {result['application']}" if result["application"] else "",
            "Trecho:",
            content,
        ]
        section = "\n".join(line for line in lines if line)
        if len(section) > remaining:
            section = section[:remaining].rstrip()
        if section:
            sections.append(section)
            remaining -= len(section) + 2
        if remaining <= 0:
            break
    return "\n\n".join(sections)
