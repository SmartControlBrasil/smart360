from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from apps.atlas_agent.api_client import AtlasAPIClient, ATLAS_IMPORT_PATH, qualified_prospects
from apps.atlas_agent.config import AtlasConfigError, AtlasPocConfig
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
        return "production-real"
    if config.mock_mode:
        return "development-mock"
    return "development-real-keys"


def _write_csv(leads, filename: str = "atlas_leads_mock.csv") -> None:
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
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


def run_pipeline(config: AtlasPocConfig) -> AtlasRunSummary:
    summary = AtlasRunSummary(mode=_safe_mode_label(config))
    print("--- ATLAS AGENT: PoC controlada iniciada ---")
    print(f"[Atlas Config] modo={summary.mode}; cidade={config.city}; segmento={config.segment}; limite={config.max_prospects_per_run}")
    print(f"[Atlas Config] endpoint oficial={ATLAS_IMPORT_PATH}; cold mail=desligado")

    scraper = SchoolScraper(google_api_key=config.google_places_api_key)
    raw_leads = scraper.run_pipeline([config.city], [config.segment])
    summary.collected = len(raw_leads)
    limited_leads = raw_leads[: config.max_prospects_per_run]
    if len(raw_leads) > len(limited_leads):
        print(f"[Atlas Limit] {len(raw_leads) - len(limited_leads)} prospects ignorados pelo limite da execucao.")
    print(f"[Atlas Scraper] coletados={summary.collected}; considerados={len(limited_leads)}")

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
        sheets_db = GoogleSheetsIntegration(spreadsheet_title="Planilha Matriz de Leads - Inteligência Comercial (PoC)")
        sheets_db.push_leads_batch(qualified_leads)
    else:
        print("[Atlas Sheets] desabilitado por ATLAS_ENABLE_SHEETS=false.")

    print("[Atlas Mailer] desabilitado por politica da Sprint Atlas 04. Nenhum e-mail sera enviado.")
    _write_csv(qualified_leads)

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
    load_dotenv()
    try:
        config = AtlasPocConfig.from_env(environ or os.environ)
    except AtlasConfigError as exc:
        print(f"[Atlas Config] erro critico: {exc}")
        return 2

    run_pipeline(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
