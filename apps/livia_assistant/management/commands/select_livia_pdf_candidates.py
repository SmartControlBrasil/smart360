import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.livia_assistant.rag.pdf_selector import select_pdf_candidates


class Command(BaseCommand):
    help = "Seleciona PDFs pequenos e relevantes para futura conversão, sem extrair conteúdo."

    def handle(self, *args, **options):
        raw_path = Path(settings.BASE_DIR) / "knowledge" / "raw_academico"
        if not raw_path.exists():
            self.stdout.write(self.style.WARNING(f"Pasta não encontrada: {raw_path}"))
            return

        selection = select_pdf_candidates(raw_path)
        report = {"generated_at": timezone.now().isoformat(), **selection}
        reports_path = Path(settings.BASE_DIR) / "knowledge" / "reports"
        reports_path.mkdir(parents=True, exist_ok=True)
        markdown_path = reports_path / "pdf_candidates.md"
        json_path = reports_path / "pdf_candidates.json"
        markdown_path.write_text(_build_markdown_report(report), encoding="utf-8")
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(f"PDFs encontrados: {selection['total_pdfs']}")
        self.stdout.write(f"Candidatos selecionados: {selection['candidate_count']}")
        self.stdout.write(f"Grandes demais ignorados: {selection['oversized_count']}")
        self.stdout.write("Top 20 candidatos:")
        for candidate in selection["candidates"][:20]:
            self.stdout.write(f"- [{candidate['score']}] {candidate['relative_path']} ({candidate['size_human']})")
        self.stdout.write(self.style.SUCCESS(f"Relatórios: {markdown_path} e {json_path}"))


def _build_markdown_report(report):
    lines = [
        "# Seleção de PDFs candidatos para a LÍVIA",
        "",
        f"- Data/hora: {report['generated_at']}",
        f"- Caminho analisado: `{report['base_path']}`",
        f"- Total de PDFs: {report['total_pdfs']}",
        f"- Total de candidatos: {report['candidate_count']}",
        f"- PDFs grandes demais (> {report['max_size_mb']} MB): {report['oversized_count']}",
        "",
        "## Top candidatos por score",
        "",
        *_candidate_table(report["candidates"]),
        "",
        "## PDFs grandes demais",
        "",
        *_candidate_table(report["oversized"]),
        "",
        "## Recomendação de conversão por lote",
        "",
        "1. Converter primeiro até 5 PDFs de maior score, revisando manualmente cada Markdown.",
        "2. Priorizar FMEA, falhas, confiabilidade, disponibilidade, TPM e manutenção.",
        "3. No lote seguinte, selecionar automação, robótica, controle, sensores e instrumentação.",
        "4. Tratar IA aplicada e dados em lote separado, validando aplicação prática.",
        "5. Não converter PDFs grandes demais ou temas penalizados sem revisão explícita.",
        "",
    ]
    return "\n".join(lines)


def _candidate_table(items):
    lines = ["| Score | Arquivo | Tamanho | Categoria | Termos | Notas |", "|---:|---|---:|---|---|---|"]
    if not items:
        return [*lines, "| - | Nenhum | - | - | - | - |"]
    lines.extend(
        f"| {item['score']} | {_escape(item['relative_path'])} | {item['size_human']} | {item['recommended_category']} | "
        f"{_escape(', '.join(item['matched_terms']))} | {_escape(item['notes'])} |"
        for item in items
    )
    return lines


def _escape(value):
    return str(value or "-").replace("|", "\\|").replace("\n", " ")
