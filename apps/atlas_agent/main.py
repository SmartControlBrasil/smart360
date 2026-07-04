from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from apps.atlas_agent.api_client import AtlasAPIClient, ATLAS_IMPORT_PATH, qualified_prospects
from apps.atlas_agent.config import AtlasConfigError, AtlasPocConfig, UNSAFE_ATLAS_TOKENS
from apps.atlas_agent.enricher import EnrichmentService
from apps.atlas_agent.scoring import ScoringEngine
from apps.atlas_agent.scraper import SchoolScraper
from apps.atlas_agent.sheets import GoogleSheetsIntegration


@dataclass
class AtlasRunSummary:
    mode: str
    collected: int = 0
    enriched: int = 0
    scored: int = 0
    qualified: int = 0
    rejected_by_score: int = 0
    sent_to_api: int = 0
    api_created_opportunities: int = 0
    api_duplicates: int = 0
    errors: list[str] = field(default_factory=list)


def _safe_mode_label(config: AtlasPocConfig) -> str:
    if config.production:
        return "production-google_places" if config.use_google_places else "production-mock"
    if config.mock_mode:
        return "development-mock"
    return "development-google_places"


def _load_env_file() -> None:
    """Carrega .env do raiz do repositório, sem sobrescrever variáveis exportadas."""
    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)


DEFAULT_MOCK_CSV_PATH = (Path(__file__).resolve().parent / "atlas_leads_mock.csv").resolve()


def _write_csv(leads, filepath: Path | str) -> None:
    try:
        path = Path(filepath)
        if not path.is_absolute():
            path = (Path(__file__).resolve().parent / path).resolve()
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Instituicao",
                "Tipo",
                "Cidade",
                "Regiao",
                "Nome_Decisor",
                "Cargo",
                "Email",
                "Telefone",
                "Status",
                "Score",
                "Notas",
            ])
            for lead in leads:
                writer.writerow(lead.to_csv_row())
        print(f"[Atlas CSV] CSV gravado com sucesso em: {path}")
    except (OSError, PermissionError) as exc:
        print(f"[Atlas CSV] Aviso: Nao foi possivel gravar o CSV de saida em {filepath}: {exc}. Continuando...")


def run_pipeline(config: AtlasPocConfig) -> AtlasRunSummary:
    summary = AtlasRunSummary(mode=_safe_mode_label(config))
    print("--- ATLAS AGENT: PoC controlada iniciada ---")
    source_label = config.source
    print(f"[Atlas Config] modo={summary.mode}; fonte={source_label}; segmento={config.segment}; cidade={config.city}; limite={config.max_prospects_per_run}; score minimo={config.min_score}")
    print(f"[Atlas Config] endpoint oficial={ATLAS_IMPORT_PATH}; cold mail=desligado")

    scraper = SchoolScraper(
        google_api_key=config.google_places_api_key,
        production=config.production,
        source=config.source,
        mock_csv_path=config.mock_csv_path,
    )
    raw_leads = scraper.run_pipeline([config.city], [config.segment], max_results=config.max_prospects_per_run)
    collected_count = getattr(scraper, "collected_count", 0)
    if isinstance(collected_count, (int, float)) and not isinstance(collected_count, bool):
        summary.collected = int(collected_count)
    else:
        summary.collected = len(raw_leads)
    limited_leads = raw_leads[: config.max_prospects_per_run]
    print(f"[Atlas Scraper] coletados={summary.collected}; considerados={len(limited_leads)}")
    limited_count = getattr(scraper, "limited_count", 0)
    if isinstance(limited_count, (int, float)) and not isinstance(limited_count, bool) and limited_count > 0:
        print(f"[Atlas Limit] {limited_count} prospects ignorados pelo limite da execucao.")
    elif len(raw_leads) > len(limited_leads):
        print(f"[Atlas Limit] {len(raw_leads) - len(limited_leads)} prospects ignorados pelo limite da execucao.")

    enricher = EnrichmentService(api_key=config.apollo_api_key)
    enriched_leads = []
    for lead in limited_leads:
        try:
            enriched_leads.append(enricher.process_lead(lead))
        except Exception as exc:  # pragma: no cover - guardrail for manual runs
            summary.errors.append(f"enrichment:{lead.institution_name}:{exc}")
    summary.enriched = len(enriched_leads)
    print(f"[Atlas Enricher] enriquecidos={summary.enriched}")

    scoring = ScoringEngine()
    scored_leads = []
    for lead in enriched_leads:
        try:
            scored_leads.append(scoring.process_lead(lead))
        except Exception as exc:  # pragma: no cover - guardrail for manual runs
            summary.errors.append(f"scoring:{lead.institution_name}:{exc}")
    summary.scored = len(scored_leads)

    qualified_leads = qualified_prospects(scored_leads, minimum_score=config.min_score)
    summary.qualified = len(qualified_leads)
    summary.rejected_by_score = len(scored_leads) - len(qualified_leads)
    print(
        f"[Atlas Score] qualificados={summary.qualified}; "
        f"rejeitados_score={summary.rejected_by_score}; minimo={config.min_score}"
    )

    if qualified_leads and config.can_sync_api:
        atlas_api = AtlasAPIClient(
            base_url=config.api_base_url,
            token=config.api_token,
            company_id=config.company_id,
        )
        try:
            import_result = atlas_api.import_prospects(qualified_leads)
            summary.sent_to_api = len(qualified_leads)
            summary.api_created_opportunities = import_result.created_opportunities
            summary.api_duplicates = import_result.skipped_duplicates
            if import_result.errors:
                summary.errors.append(f"api_batch_errors:{len(import_result.errors)}")
            print(
                f"[Atlas API] enviados={summary.sent_to_api}; "
                f"commercial_opportunities={summary.api_created_opportunities}; duplicadas={summary.api_duplicates}"
            )
        except Exception as exc:
            summary.errors.append(f"api:{exc}")
            print("[Atlas API] falha na sincronizacao oficial; token/chaves nao exibidos.")
    elif qualified_leads:
        print("[Atlas API] sincronizacao pulada: credenciais oficiais ausentes ou inseguras para esta execucao.")
    else:
        print("[Atlas API] sincronizacao pulada: nenhum prospect atingiu o score minimo.")

    if config.enable_sheets:
        has_credentials = bool(config.google_application_credentials)
        has_spreadsheet_id = bool(config.spreadsheet_id)
        print(
            "[Atlas Sheets] habilitado; credencial={cred}; spreadsheet_id={sheet}.".format(
                cred="presente" if has_credentials else "ausente",
                sheet="presente" if has_spreadsheet_id else "ausente",
            )
        )
        sheets_db = GoogleSheetsIntegration(
            spreadsheet_title="Planilha Matriz de Leads - Inteligência Comercial (PoC)",
            spreadsheet_id=config.spreadsheet_id,
            credentials_path=config.google_application_credentials,
        )
        try:
            sheets_db.push_leads_batch(qualified_leads)
        except Exception as exc:  # pragma: no cover - guardrail for manual runs
            summary.errors.append(f"sheets:{exc}")
            print("[Atlas Sheets] falha resumida na gravacao; fluxo principal mantido.")
    else:
        print("[Atlas Sheets] desabilitado por ATLAS_ENABLE_SHEETS=false.")

    print("[Atlas Mailer] desabilitado por politica da Sprint Atlas 04. Nenhum e-mail sera enviado.")
    if config.write_csv_output:
        raw_path = config.mock_csv_path or config.csv_output_path
        if raw_path:
            csv_path = Path(raw_path)
            if not csv_path.is_absolute():
                csv_path = (Path(__file__).resolve().parent / csv_path).resolve()
        else:
            csv_path = DEFAULT_MOCK_CSV_PATH
        _write_csv(qualified_leads, csv_path)
    else:
        print("[Atlas CSV] Gravacao do CSV de saida desabilitada por ATLAS_WRITE_CSV_OUTPUT=false.")

    print("--- ATLAS AGENT: resumo final ---")
    print(
        "coletados={collected}; enriquecidos={enriched}; qualificados={qualified}; "
        "rejeitados_score={rejected}; enviados_api={sent}; erros={errors}".format(
            collected=summary.collected,
            enriched=summary.enriched,
            qualified=summary.qualified,
            rejected=summary.rejected_by_score,
            sent=summary.sent_to_api,
            errors=len(summary.errors),
        )
    )
    print("Revise oportunidades em: Admin Shell > Atlas Comercial (/app/atlas/opportunities/)")
    return summary


def main(environ: dict[str, str] | None = None) -> int:
    _load_env_file()
    try:
        config = AtlasPocConfig.from_env(environ or os.environ)
    except AtlasConfigError as exc:
        print(f"[Atlas Config] erro critico: {exc}")
        return 2

    if config.validate_only:
        print("--- ATLAS AGENT: Modo Pre-Validacao ---")
        print(f"[Atlas Config] ambiente={config.env}; fonte={config.source}; cidade={config.city}; segmento={config.segment}; limite={config.max_prospects_per_run}; score minimo={config.min_score}")
        print(f"[Atlas Config] Google Places API Key: {'Presente' if config.google_places_api_key else 'Ausente'}")
        print(f"[Atlas Config] API Token: {'Presente' if config.api_token and config.api_token not in UNSAFE_ATLAS_TOKENS else 'Ausente'}")
        print(f"[Atlas Config] Sheets: {'Habilitado' if config.enable_sheets else 'Desabilitado'}")
        print(f"[Atlas Config] Spreadsheet ID: {'Presente' if config.spreadsheet_id else 'Ausente'}")
        print(
            "[Atlas Config] Credencial Google Application: {status}".format(
                status="Presente" if config.google_application_credentials else "Ausente",
            )
        )
        if config.production and config.source == "google_places":
            print("[Atlas Config] Configuração production validada para rodada real manual.")
        else:
            print("[Atlas Config] Pré-validação development/mock concluída. Para rodada real, use ATLAS_ENV=production com ATLAS_API_TOKEN e GOOGLE_PLACES_API_KEY reais.")
        return 0

    run_pipeline(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
