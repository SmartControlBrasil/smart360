import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader


MIN_USEFUL_CHARACTERS = 500
APPLICATION_GUIDANCE = """## Aplicação para a Smart Control Brasil

Este material deve apoiar respostas técnicas da LÍVIA sobre manutenção, automação, confiabilidade, diagnóstico, TPM, FMEA, falhas ou engenharia, conectando conceitos à aplicação prática da Smart Control Brasil.

A LÍVIA não deve usar este material para prometer preço, prazo, estoque, garantia ou resultado comercial."""


def normalize_pdf_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    normalized = []
    previous_blank = False
    for line in lines:
        if not line:
            if normalized and not previous_blank:
                normalized.append("")
            previous_blank = True
            continue
        normalized.append(line)
        previous_blank = False
    return "\n".join(normalized).strip()


def extract_pdf_text(path, max_pages=None):
    reader = PdfReader(str(path))
    pages = reader.pages[:max_pages] if max_pages is not None else reader.pages
    extracted_pages = []
    for page in pages:
        page_text = normalize_pdf_text(page.extract_text() or "")
        if page_text:
            extracted_pages.append(page_text)
    return "\n\n".join(extracted_pages)


def infer_pdf_output_category(path):
    normalized = _normalize_for_matching(path)
    if any(term in normalized for term in ("fmea", "falha", "falhas", "confiabilidade", "disponibilidade", "tpm", "manutencao", "preventiva", "preditiva", "planejada", "autonoma")):
        return "manutencao"
    if any(term in normalized for term in ("automacao", "controle", "clp", "sensor", "sensores", "instrumentacao", "robotica")):
        return "engenharia"
    if any(term in normalized for term in ("inteligencia artificial", "dados")) or re.search(r"\bia\b", normalized):
        return "ia_aplicada"
    return "academico"


def build_pdf_markdown(source_path, extracted_text, category):
    source_path = Path(source_path)
    source_reference = _source_reference(source_path)
    title = source_path.stem.replace("_", " ").strip()
    return (
        f"# {title}\n\n"
        f"> Fonte original: {source_reference}  \n"
        f"> Categoria: {category}  \n"
        "> Material convertido para apoio técnico da LÍVIA Assistant.\n\n"
        "## Conteúdo extraído\n\n"
        f"{normalize_pdf_text(extracted_text)}\n\n"
        f"{APPLICATION_GUIDANCE}\n"
    )


def convert_pdf_to_markdown(source_path, output_base_path):
    source_path = Path(source_path)
    output_base_path = Path(output_base_path)
    if source_path.suffix.lower() != ".pdf":
        return _result("ignored", source_path, reason="source is not a PDF")

    category = infer_pdf_output_category(source_path)
    source_reference = _source_reference(source_path)
    output_directory = output_base_path / category
    output_path = _find_output_path(output_directory, _slugify_filename(source_path.stem), source_reference)
    if output_path.exists() and _belongs_to_source(output_path, source_reference):
        return _result("ignored", source_path, output_path, "Markdown already exists for this source", category)

    try:
        extracted_text = normalize_pdf_text(extract_pdf_text(source_path))
    except Exception as exc:
        return _result("error", source_path, reason=f"PDF extraction failed: {exc}", category=category)

    useful_characters = len(re.sub(r"\s+", "", extracted_text))
    if _looks_like_garbled_pdf_text(extracted_text):
        return _result("error", source_path, reason="extracted text appears corrupted or unreadable", category=category)
    if useful_characters < MIN_USEFUL_CHARACTERS:
        return _result("ignored", source_path, reason="extracted text has fewer than 500 useful characters", category=category)

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_pdf_markdown(source_path, extracted_text, category), encoding="utf-8")
    return _result("converted", source_path, output_path, category=category)


def _looks_like_garbled_pdf_text(text):
    slash_number_tokens = len(re.findall(r"/\d+", text))
    word_tokens = len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", text))
    return slash_number_tokens > 100 and slash_number_tokens > word_tokens * 2

def _find_output_path(directory, slug, source_reference):
    candidate = directory / f"{slug}.md"
    suffix = 2
    while candidate.exists() and not _belongs_to_source(candidate, source_reference):
        candidate = directory / f"{slug}_{suffix}.md"
        suffix += 1
    return candidate


def _belongs_to_source(path, source_reference):
    try:
        return f"> Fonte original: {source_reference}  " in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _source_reference(path):
    path = Path(path)
    if "raw_academico" in path.parts:
        index = path.parts.index("raw_academico")
        return Path(*path.parts[index:]).as_posix()
    return path.as_posix()


def _slugify_filename(value):
    value = _normalize_for_matching(value)
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_") or "pdf_convertido"


def _normalize_for_matching(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(character for character in value if not unicodedata.combining(character))


def _result(status, source_path, output_path=None, reason="", category=""):
    return {
        "status": status,
        "source_path": str(source_path),
        "output_path": str(output_path) if output_path else None,
        "reason": reason,
        "category": category,
    }
