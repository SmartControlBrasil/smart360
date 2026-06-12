from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.livia_assistant.rag.text_extractor import convert_raw_file_to_markdown


class Command(BaseCommand):
    help = "Converte seletivamente TXT e DOCX brutos em Markdown aprovado para revisão da Lívia."

    def handle(self, *args, **options):
        raw_path = Path(settings.BASE_DIR) / "knowledge" / "raw_academico"
        if not raw_path.exists():
            self.stdout.write(self.style.WARNING(f"Pasta não encontrada: {raw_path}"))
            return

        candidates = sorted(path for path in raw_path.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".docx"})
        results = [convert_raw_file_to_markdown(path, Path(settings.BASE_DIR) / "knowledge") for path in candidates]
        converted = [result for result in results if result["status"] == "converted"]
        ignored = [result for result in results if result["status"] == "ignored"]
        errors = [result for result in results if result["status"] == "error"]

        self.stdout.write(f"Arquivos encontrados: {len(candidates)}")
        self.stdout.write(f"Convertidos: {len(converted)}")
        self.stdout.write(f"Ignorados: {len(ignored)}")
        self.stdout.write(f"Erros: {len(errors)}")
        if converted:
            self.stdout.write("Arquivos gerados:")
            for result in converted:
                self.stdout.write(f"- {result['output_path']}")
        for result in ignored:
            self.stdout.write(self.style.WARNING(f"[ignorado] {result['source_path']}: {result['reason']}"))
        for result in errors:
            self.stderr.write(self.style.ERROR(f"[erro] {result['source_path']}: {result['reason']}"))
