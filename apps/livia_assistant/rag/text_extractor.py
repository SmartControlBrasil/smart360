import re
import unicodedata
from pathlib import Path


MIN_USEFUL_CHARACTERS = 200
APPLICATION_GUIDANCE = """## Aplicação para a Smart Control Brasil

Este material deve ser usado pela LÍVIA como apoio técnico para explicar conceitos de forma prática, conectando engenharia, manutenção, automação, confiabilidade, TPM, IA ou robótica às soluções da Smart Control Brasil.

A LÍVIA não deve citar este material como promessa comercial, preço, prazo, estoque ou garantia."""


class DocxDependencyError(RuntimeError):
    pass


def normalize_extracted_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    normalized_lines = []
    previous_blank = False
    for line in lines:
        if not line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False
    return "\n".join(normalized_lines).strip()


def slugify_filename(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return value or "material_convertido"


def infer_output_category_from_path(path):
    normalized = _normalize_for_matching(str(path))
    if any(term in normalized for term in ("manutencao produtiva total", "tpm", "manutencao")):
        return "manutencao"
    if any(term in normalized for term in ("engenharia de controle e automacao", "automacao", "controle")):
        return "engenharia"
    if any(term in normalized for term in ("inteligenicia artificial", "inteligencia artificial", "ia aplicada")) or re.search(r"\bia\b", normalized):
        return "ia_aplicada"
    return "academico"


def extract_txt(path):
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def extract_docx(path):
    try:
        from docx import Document
    except ImportError as exc:
        raise DocxDependencyError("python-docx is not installed; DOCX conversion skipped") from exc

    document = Document(str(path))
    blocks = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            blocks.append("")
        elif paragraph.style and paragraph.style.name.lower().startswith("heading"):
            level_match = re.search(r"(\d+)", paragraph.style.name)
            level = min(int(level_match.group(1)), 6) if level_match else 2
            blocks.append(f"{'#' * level} {text}")
        else:
            blocks.append(text)
    return "\n\n".join(blocks)


def convert_raw_file_to_markdown(source_path, output_base_path):
    source_path = Path(source_path)
    output_base_path = Path(output_base_path)
    if source_path.name.startswith("~$"):
        return {"status": "ignored", "reason": "temporary Office file", "source_path": str(source_path), "output_path": None}

    extension = source_path.suffix.lower()
    if extension not in {".txt", ".docx"}:
        return {"status": "ignored", "reason": "unsupported extension for this conversion stage", "source_path": str(source_path), "output_path": None}

    try:
        extracted = extract_txt(source_path) if extension == ".txt" else extract_docx(source_path)
    except (OSError, DocxDependencyError, ValueError) as exc:
        return {"status": "error", "reason": str(exc), "source_path": str(source_path), "output_path": None}

    content = normalize_extracted_text(extracted)
    useful_characters = len(re.sub(r"\s+", "", content))
    if useful_characters < MIN_USEFUL_CHARACTERS:
        return {"status": "ignored", "reason": "extracted text has fewer than 200 useful characters", "source_path": str(source_path), "output_path": None}

    category = infer_output_category_from_path(source_path)
    title = _infer_title(source_path, content)
    source_reference = _source_reference(source_path)
    markdown = (
        f"# {title}\n\n"
        f"> Fonte original: {source_reference}  \n"
        f"> Categoria: {category}  \n"
        "> Material convertido para apoio técnico da LÍVIA Assistant.\n\n"
        "## Conteúdo extraído\n\n"
        f"{content}\n\n"
        f"{APPLICATION_GUIDANCE}\n"
    )
    output_directory = output_base_path / category
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = _available_output_path(output_directory, slugify_filename(source_path.stem), source_reference)
    output_path.write_text(markdown, encoding="utf-8")
    return {"status": "converted", "reason": "", "source_path": str(source_path), "output_path": str(output_path), "category": category}


def _infer_title(path, content):
    for line in content.splitlines():
        candidate = line.lstrip("# ").strip()
        if 3 <= len(candidate) <= 160:
            return candidate
    return Path(path).stem.replace("_", " ").strip().title()


def _source_reference(path):
    path = Path(path)
    parts = path.parts
    if "raw_academico" in parts:
        index = parts.index("raw_academico")
        return Path(*parts[index:]).as_posix()
    return path.as_posix()


def _available_output_path(directory, slug, source_reference):
    candidate = directory / f"{slug}.md"
    suffix = 2
    source_marker = f"> Fonte original: {source_reference}  "
    while candidate.exists():
        try:
            if source_marker in candidate.read_text(encoding="utf-8", errors="ignore"):
                return candidate
        except OSError:
            pass
        candidate = directory / f"{slug}_{suffix}.md"
        suffix += 1
    return candidate


def _normalize_for_matching(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(character for character in value if not unicodedata.combining(character))
