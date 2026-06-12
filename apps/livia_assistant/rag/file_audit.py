import hashlib
from collections import Counter
from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}
IGNORED_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mp3", ".xlsx", ".pptx", ".html", ".htm",
}
HASH_SKIP_THRESHOLD_BYTES = 50 * 1024 * 1024


def human_readable_size(size_bytes):
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024


def calculate_file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def infer_category_from_path(path):
    path = Path(path)
    parts = [part for part in path.parts if part not in {".", "..", path.anchor}]
    return parts[0] if len(parts) > 1 else "sem_categoria"


def is_supported_extension(extension):
    return _normalize_extension(extension) in SUPPORTED_EXTENSIONS


def is_ignored_extension(extension):
    return _normalize_extension(extension) in IGNORED_EXTENSIONS


def audit_raw_knowledge_directory(base_path, large_file_threshold_mb=20):
    base_path = Path(base_path)
    threshold_bytes = large_file_threshold_mb * 1024 * 1024
    files = []
    hashes = {}

    if not base_path.exists():
        return _build_summary(base_path, files)

    for path in sorted(item for item in base_path.rglob("*") if item.is_file()):
        relative_path = path.relative_to(base_path).as_posix()
        extension = path.suffix.lower()
        size_bytes = path.stat().st_size
        notes = []
        sha256 = None
        duplicate_of = None

        if size_bytes > HASH_SKIP_THRESHOLD_BYTES:
            notes.append("hash skipped due to size")
        else:
            try:
                sha256 = calculate_file_hash(path)
            except OSError as exc:
                notes.append(f"hash failed: {exc}")

        if sha256:
            duplicate_of = hashes.get(sha256)
            if duplicate_of:
                notes.append("possible duplicate by sha256")
            else:
                hashes[sha256] = relative_path

        supported = is_supported_extension(extension)
        ignored = is_ignored_extension(extension)
        if not supported and not ignored:
            notes.append("extension not classified")

        files.append({
            "relative_path": relative_path,
            "filename": path.name,
            "extension": extension or "[no extension]",
            "size_bytes": size_bytes,
            "size_human": human_readable_size(size_bytes),
            "inferred_category": infer_category_from_path(Path(relative_path)),
            "supported_for_initial_ingestion": supported,
            "ignored_for_now": ignored,
            "too_large": size_bytes > threshold_bytes,
            "sha256": sha256,
            "duplicate_of": duplicate_of,
            "notes": "; ".join(notes),
        })

    return _build_summary(base_path, files)


def _normalize_extension(extension):
    extension = str(extension or "").lower().strip()
    return extension if extension.startswith(".") else f".{extension}"


def _build_summary(base_path, files):
    extension_counts = Counter(file_info["extension"] for file_info in files)
    return {
        "base_path": str(Path(base_path).resolve()),
        "total_files": len(files),
        "total_size_bytes": sum(file_info["size_bytes"] for file_info in files),
        "total_size_human": human_readable_size(sum(file_info["size_bytes"] for file_info in files)),
        "extension_counts": dict(sorted(extension_counts.items())),
        "supported_count": sum(file_info["supported_for_initial_ingestion"] for file_info in files),
        "ignored_count": sum(file_info["ignored_for_now"] for file_info in files),
        "too_large_count": sum(file_info["too_large"] for file_info in files),
        "duplicate_count": sum(bool(file_info["duplicate_of"]) for file_info in files),
        "files": files,
    }
