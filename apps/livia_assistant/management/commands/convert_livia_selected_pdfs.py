from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.livia_assistant.rag.pdf_extractor import convert_pdf_to_markdown, find_existing_pdf_markdown
from apps.livia_assistant.rag.pdf_selector import normalize_search_text, select_pdf_candidates


ALLOWED_CATEGORIES = ("manutencao", "engenharia", "ia_aplicada", "academico")


class Command(BaseCommand):
    help = "Converte lotes controlados de PDFs técnicos selecionados em Markdown revisável."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5, help="Máximo de PDFs a converter nesta execução.")
        parser.add_argument("--offset", type=int, default=0, help="Quantidade de candidatos filtrados a pular.")
        parser.add_argument("--category", choices=ALLOWED_CATEGORIES, help="Filtra pela categoria recomendada.")
        parser.add_argument("--include-term", action="append", default=[], help="Filtra caminho/nome pelo termo; pode ser repetido.")
        parser.add_argument("--dry-run", action="store_true", help="Mostra o lote sem gerar Markdown.")
        parser.add_argument("--force", action="store_true", help="Sobrescreve Markdown existente da mesma fonte.")

    def handle(self, *args, **options):
        limit = options["limit"]
        offset = options["offset"]
        if limit < 1:
            raise CommandError("--limit deve ser maior que zero.")
        if offset < 0:
            raise CommandError("--offset não pode ser negativo.")

        raw_path = Path(settings.BASE_DIR) / "knowledge" / "raw_academico"
        if not raw_path.exists():
            self.stdout.write(self.style.WARNING(f"Pasta não encontrada: {raw_path}"))
            return

        selection = select_pdf_candidates(raw_path, max_size_mb=20, limit=100000)
        candidates = selection["candidates"]
        filtered = self._apply_filters(candidates, options["category"], options["include_term"])
        output_base_path = Path(settings.BASE_DIR) / "knowledge"
        existing_candidates = [] if options["force"] else [
            candidate for candidate in filtered
            if find_existing_pdf_markdown(raw_path / candidate["relative_path"], output_base_path)
        ]
        available = [candidate for candidate in filtered if candidate not in existing_candidates]
        selected = available[offset : offset + limit]
        skipped_by_filters = len(candidates) - len(filtered)
        skipped_by_offset_limit = len(available) - len(selected)
        ignored_score_limit_size = selection["total_pdfs"] - len(candidates) + skipped_by_filters + skipped_by_offset_limit

        if options["dry_run"]:
            results = []
            self.stdout.write(self.style.WARNING("Dry-run: nenhum Markdown será gerado."))
            self.stdout.write("PDFs que seriam convertidos:")
            for candidate in selected:
                self.stdout.write(f"- [{candidate['score']}] {candidate['relative_path']} ({candidate['recommended_category']})")
        else:
            results = [
                convert_pdf_to_markdown(
                    raw_path / candidate["relative_path"],
                    Path(settings.BASE_DIR) / "knowledge",
                    force=options["force"],
                )
                for candidate in selected
            ]

        converted = [result for result in results if result["status"] == "converted"]
        existing = [result for result in results if result["status"] == "ignored" and "already exists" in result["reason"]]
        ignored_other = [result for result in results if result["status"] == "ignored" and result not in existing]
        errors = [result for result in results if result["status"] == "error"]

        self.stdout.write(f"PDFs candidatos avaliados: {len(candidates)}")
        self.stdout.write(f"PDFs após filtros: {len(filtered)}")
        self.stdout.write(f"PDFs selecionados no lote: {len(selected)}")
        self.stdout.write(f"PDFs convertidos: {len(converted)}")
        self.stdout.write(f"PDFs ignorados por já existir: {len(existing_candidates) + len(existing)}")
        self.stdout.write(f"PDFs ignorados por score/limite/tamanho: {ignored_score_limit_size}")
        self.stdout.write(f"Erros: {len(errors)}")
        if converted:
            self.stdout.write("Arquivos Markdown gerados:")
            for result in converted:
                self.stdout.write(f"- {result['output_path']}")
        for result in [*existing, *ignored_other]:
            self.stdout.write(self.style.WARNING(f"[ignorado] {result['source_path']}: {result['reason']}"))
        for result in errors:
            self.stderr.write(self.style.ERROR(f"[erro] {result['source_path']}: {result['reason']}"))

    def _apply_filters(self, candidates, category, include_terms):
        normalized_terms = [normalize_search_text(term) for term in include_terms if normalize_search_text(term)]
        filtered = []
        for candidate in candidates:
            if category and candidate["recommended_category"] != category:
                continue
            path_text = normalize_search_text(candidate["relative_path"])
            if normalized_terms and not any(term in path_text for term in normalized_terms):
                continue
            filtered.append(candidate)
        return filtered
