import os
import csv
from dotenv import load_dotenv
from apps.atlas_agent.scraper import SchoolScraper
from apps.atlas_agent.enricher import EnrichmentService
from apps.atlas_agent.sheets import GoogleSheetsIntegration
from apps.atlas_agent.mailer import ColdMailer
from apps.atlas_agent.api_client import AtlasAPIClient, DEFAULT_MIN_SCORE, qualified_prospects

# Carrega variáveis do arquivo .env
load_dotenv()

def main():
    print("--- ATLAS AGENT: Iniciando Pipeline Completo ---")
    
    regions = ["Vila Mariana"]
    queries = ["escola particular"]
    
    # Chaves de Ambiente
    google_places_key = os.getenv("ATLAS_GOOGLE_PLACES_KEY")
    apollo_key = os.getenv("ATLAS_APOLLO_KEY")
    smtp_user = os.getenv("ATLAS_SMTP_USER", "")
    smtp_pass = os.getenv("ATLAS_SMTP_PASS", "")
    api_base_url = os.getenv("ATLAS_API_BASE_URL", "http://127.0.0.1:8000")
    api_token = os.getenv("ATLAS_API_TOKEN", "")
    company_id = int(os.getenv("ATLAS_COMPANY_ID", "0"))
    minimum_score = int(os.getenv("ATLAS_MIN_SCORE", str(DEFAULT_MIN_SCORE)))

    atlas_api = AtlasAPIClient(
        base_url=api_base_url,
        token=api_token,
        company_id=company_id,
    )
    
    # 1. Scraper
    scraper = SchoolScraper(google_api_key=google_places_key)
    leads = scraper.run_pipeline(regions, queries)
    
    # 2. Enrichment
    enricher = EnrichmentService(api_key=apollo_key)
    enriched_leads = []
    for lead in leads:
        enriched = enricher.process_lead(lead)
        enriched_leads.append(enriched)

    qualified_leads = qualified_prospects(enriched_leads, minimum_score=minimum_score)
    skipped_count = len(enriched_leads) - len(qualified_leads)
    print(
        f"[Atlas Score] {len(qualified_leads)} prospects qualificados; "
        f"{skipped_count} abaixo do score minimo {minimum_score}."
    )
    if not qualified_leads:
        raise RuntimeError("Nenhum prospect atingiu o score minimo para a API oficial do Atlas.")

    # 3. API oficial Atlas: cria CommercialOpportunity para revisao humana.
    import_result = atlas_api.import_prospects(qualified_leads)
    print(
        f"[Atlas API] Lote {import_result.public_id} ({import_result.status}): "
        f"{import_result.created_opportunities} oportunidades criadas, "
        f"{import_result.skipped_duplicates} duplicadas."
    )

    # 4. Sheets Integration (Precisa do arquivo credentials.json na raiz do projeto)
    sheets_db = GoogleSheetsIntegration(spreadsheet_title="Planilha Matriz de Leads - Inteligência Comercial (PoC)")
    sheets_db.push_leads_batch(qualified_leads)
    
    # 5. Cold Mailing (sempre em dry-run nesta PoC)
    mailer = ColdMailer(smtp_user=smtp_user, smtp_pass=smtp_pass, dry_run=True)
    mailer.run_campaign(qualified_leads)
    
    # Backup CSV local
    csv_filename = "atlas_leads_mock.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Instituicao", "Tipo", "Cidade", "Regiao", "Nome_Decisor", 
            "Cargo", "Email", "Telefone", "Status", "Score", "Notas"
        ])
        for lead in qualified_leads:
            writer.writerow(lead.to_csv_row())
            
    print(f"--- Pipeline Concluido! {len(qualified_leads)} prospects enviados para revisao. ---")
    print(f"Salvo em: {csv_filename}")

if __name__ == "__main__":
    main()
