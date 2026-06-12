from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.livia_assistant.rag.importer import import_knowledge_directory


class Command(BaseCommand):
    help = "Importa recursivamente a base Markdown do RAG da Lívia."

    def handle(self, *args, **options):
        knowledge_path = Path(settings.BASE_DIR) / "knowledge"
        summary = import_knowledge_directory(knowledge_path)
        self.stdout.write(f"Documentos importados: {summary['created']}")
        self.stdout.write(f"Documentos atualizados: {summary['updated']}")
        self.stdout.write(f"Chunks criados: {summary['chunks_created']}")
        self.stdout.write(f"Arquivos ignorados: {summary['ignored']}")
        self.stdout.write(f"Erros encontrados: {len(summary['errors'])}")
        for error in summary["errors"]:
            self.stderr.write(self.style.ERROR(f"{error['path']}: {error['error']}"))
