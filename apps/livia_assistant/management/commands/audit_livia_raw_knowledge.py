import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.livia_assistant.rag.file_audit import audit_raw_knowledge_directory


RECOMMENDATIONS = [
    "Começar por arquivos .txt e .docx.",
    "Priorizar PDFs menores que 20 MB.",
    "Converter materiais úteis para Markdown antes de alimentar o RAG.",
    "Priorizar automação, manutenção, TPM, confiabilidade, IA aplicada, robótica e diagnóstico técnico.",
    "Evitar conteúdo jurídico, economia e temas genéricos sem revisão.",
    "Não enviar knowledge/raw_academico/ para produção/VPS.",
    "Não versionar knowledge/raw_academico/ no Git.",
]


class Command(BaseCommand):
    help = "Audita materiais brutos acadêmicos sem extrair ou importar conteúdo."

    def handle(self, *args, **options):
        raw_path = Path(settings.BASE_DIR) / "knowledge" / "raw_academico"
        if not raw_path.exists():
            self.stdout.write(self.style.WARNING(f"Pasta não encontrada: {raw_path}"))
            return

        audit = audit_raw_knowledge_directory(raw_path)
        generated_at = timezone.now().isoformat()
        report_data = {"generated_at": generated_at, **audit}
        reports_path = Path(settings.BASE_DIR) / "knowledge" / "reports"
        reports_path.mkdir(parents=True, exist_ok=True)
        json_path = reports_path / "raw_academico_audit.json"
        markdown_path = reports_path / "raw_academico_audit.md"
        json_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(_build_markdown_report(report_data), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Auditoria concluída: {audit['total_files']} arquivos."))
        self.stdout.write(f"Tamanho total: {audit['total_size_human']}")
        self.stdout.write(f"Arquivos acima de 20 MB: {audit['too_large_count']}")
        self.stdout.write(f"Possíveis duplicados: {audit['duplicate_count']}")
        self.stdout.write(f"Relatórios: {markdown_path} e {json_path}")


def _build_markdown_report(audit):
    files = audit["files"]
    largest = sorted(files, key=lambda item: item["size_bytes"], reverse=True)[:20]
    supported = [item for item in files if item["supported_for_initial_ingestion"]]
    ignored = [item for item in files if item["ignored_for_now"]]
    duplicates = [item for item in files if item["duplicate_of"]]
    lines = [
        "# Auditoria de materiais brutos acadêmicos",
        "",
        f"- Data/hora da auditoria: {audit['generated_at']}",
        f"- Caminho auditado: `{audit['base_path']}`",
        f"- Total de arquivos: {audit['total_files']}",
        f"- Tamanho total: {audit['total_size_human']}",
        f"- Arquivos suportados para ingestão inicial: {audit['supported_count']}",
        f"- Arquivos ignorados por enquanto: {audit['ignored_count']}",
        f"- Arquivos grandes demais (> 20 MB): {audit['too_large_count']}",
        f"- Possíveis duplicados: {audit['duplicate_count']}",
        "",
        "## Quantidade por extensão",
        "",
        "| Extensão | Quantidade |",
        "|---|---:|",
    ]
    lines.extend(f"| {_escape(extension)} | {count} |" for extension, count in audit["extension_counts"].items())
    lines.extend(["", "## Top 20 maiores arquivos", "", *_file_table(largest)])
    lines.extend(["", "## Possíveis duplicados", "", *_duplicate_table(duplicates)])
    lines.extend(["", "## Arquivos suportados para ingestão inicial", "", *_file_table(supported)])
    lines.extend(["", "## Arquivos ignorados por enquanto", "", *_file_table(ignored)])
    lines.extend(["", "## Recomendações práticas", ""])
    lines.extend(f"- {recommendation}" for recommendation in RECOMMENDATIONS)
    lines.append("")
    return "\n".join(lines)


def _file_table(files):
    lines = ["| Arquivo | Extensão | Tamanho | Categoria | Grande demais | Notas |", "|---|---|---:|---|---|---|"]
    if not files:
        return [*lines, "| Nenhum | - | - | - | - | - |"]
    lines.extend(
        f"| {_escape(item['relative_path'])} | {_escape(item['extension'])} | {item['size_human']} | "
        f"{_escape(item['inferred_category'])} | {'sim' if item['too_large'] else 'não'} | {_escape(item['notes'])} |"
        for item in files
    )
    return lines


def _duplicate_table(files):
    lines = ["| Arquivo | Duplicado de | SHA-256 |", "|---|---|---|"]
    if not files:
        return [*lines, "| Nenhum | - | - |"]
    lines.extend(f"| {_escape(item['relative_path'])} | {_escape(item['duplicate_of'])} | `{item['sha256']}` |" for item in files)
    return lines


def _escape(value):
    return str(value or "-").replace("|", "\\|").replace("\n", " ")
