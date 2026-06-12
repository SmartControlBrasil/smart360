from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.livia_assistant.rag.pdf_extractor import convert_pdf_to_markdown
from apps.livia_assistant.rag.pdf_selector import select_pdf_candidates


class Command(BaseCommand):
    help = "Converte somente os cinco PDFs técnicos de maior score em Markdown revisável."

    def handle(self, *args, **options):
        raw_path = Path(settings.BASE_DIR) / "knowledge" / "raw_academico"
        if not raw_path.exists():
            self.stdout.write(self.style.WARNING(f"Pasta não encontrada: {raw_path}"))
            return

        selection = select_pdf_candidates(raw_path, max_size_mb=20, limit=5)
        results = [convert_pdf_to_markdown(raw_path / candidate["relative_path"], Path(settings.BASE_DIR) / "knowledge") for candidate in selection["candidates"]]
        converted = [result for result in results if result["status"] == "converted"]
        ignored = [result for result in results if result["status"] == "ignored"]
        errors = [result for result in results if result["status"] == "error"]

        self.stdout.write(f"PDFs candidatos avaliados: {len(selection['candidates'])}")
        self.stdout.write(f"PDFs convertidos: {len(converted)}")
        self.stdout.write(f"PDFs ignorados: {len(ignored) + selection['oversized_count']}")
        self.stdout.write(f"PDFs grandes ignorados: {selection['oversized_count']}")
        self.stdout.write(f"Erros: {len(errors)}")
        if converted:
            self.stdout.write("Arquivos Markdown gerados:")
            for result in converted:
                self.stdout.write(f"- {result['output_path']}")
        for result in ignored:
            self.stdout.write(self.style.WARNING(f"[ignorado] {result['source_path']}: {result['reason']}"))
        for result in errors:
            self.stderr.write(self.style.ERROR(f"[erro] {result['source_path']}: {result['reason']}"))
