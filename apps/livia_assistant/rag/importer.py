import hashlib
import os
import re
from pathlib import Path

from django.db import transaction
from django.utils.text import slugify

from apps.livia_assistant.models import LiviaKnowledgeChunk, LiviaKnowledgeDocument

from .chunking import split_text_into_chunks


def normalize_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def calculate_content_hash(text):
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _title_from_content(content, path):
    heading = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
    return heading.group(1).strip() if heading else path.stem.replace("_", " ").title()


def _infer_fields(path, category=None, product=None, application=None):
    parent = path.parent.name
    stem = path.stem
    if parent == "xyron":
        product = product or stem.replace("_", " ").title()
        category = category or "robotica"
    elif parent == "aplicacoes":
        application = application or stem.replace("_", " ")
        category = category or "aplicacoes"
    else:
        category = category or parent
    return category or "", product or "", application or ""


@transaction.atomic
def import_markdown_file(path, category=None, product=None, application=None):
    path = Path(path)
    content = normalize_text(path.read_text(encoding="utf-8"))
    content_hash = calculate_content_hash(content)
    category, product, application = _infer_fields(path, category, product, application)
    source_path = str(path.resolve())
    metadata = {"filename": path.name, "category": category, "product": product, "application": application, "source_path": source_path}
    document = LiviaKnowledgeDocument.objects.filter(source_path=source_path).first()
    if document and document.content_hash == content_hash:
        if not document.is_active:
            document.is_active = True
            document.save(update_fields=["is_active", "updated_at"])
        return {"document": document, "status": "ignored", "chunks_created": 0}

    defaults = {
        "title": _title_from_content(content, path), "source_type": "markdown", "category": category,
        "product": product, "application": application, "content_hash": content_hash, "metadata": metadata, "is_active": True,
    }
    if document:
        for field, value in defaults.items():
            setattr(document, field, value)
        document.save()
        document.chunks.all().delete()
        status = "updated"
    else:
        base_slug = slugify(f"{path.parent.name}-{path.stem}") or content_hash[:12]
        slug = base_slug
        suffix = 2
        while LiviaKnowledgeDocument.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        document = LiviaKnowledgeDocument.objects.create(slug=slug, source_path=source_path, **defaults)
        status = "created"

    chunks = [
        LiviaKnowledgeChunk(document=document, content=chunk, chunk_index=index, token_estimate=max(1, len(chunk) // 4), metadata=metadata)
        for index, chunk in enumerate(split_text_into_chunks(content))
    ]
    LiviaKnowledgeChunk.objects.bulk_create(chunks)
    return {"document": document, "status": status, "chunks_created": len(chunks)}


IGNORED_KNOWLEDGE_DIRECTORIES = {"raw_academico", "reports"}


def _is_ignored_directory(name):
    return name in IGNORED_KNOWLEDGE_DIRECTORIES or name.startswith(".") or name.startswith("__")


def _is_ignored_markdown_file(name):
    return name.startswith((".", "__", "~$"))


def _iter_markdown_files(base_path):
    for root, directory_names, filenames in os.walk(base_path):
        directory_names[:] = sorted(name for name in directory_names if not _is_ignored_directory(name))
        root_path = Path(root)
        for filename in sorted(filenames):
            if filename.lower().endswith(".md") and not _is_ignored_markdown_file(filename):
                yield root_path / filename


def import_knowledge_directory(base_path):
    base_path = Path(base_path)
    summary = {"created": 0, "updated": 0, "chunks_created": 0, "ignored": 0, "errors": []}
    if not base_path.exists():
        return summary
    for path in _iter_markdown_files(base_path):
        try:
            result = import_markdown_file(path)
            summary[result["status"]] += 1
            summary["chunks_created"] += result["chunks_created"]
        except Exception as exc:
            summary["errors"].append({"path": str(path), "error": str(exc)})
    return summary
