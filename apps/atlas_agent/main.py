import os
import csv
from dotenv import load_dotenv
from apps.atlas_agent.scraper import SchoolScraper
from apps.atlas_agent.enricher import EnrichmentService
from apps.atlas_agent.sheets import GoogleSheetsIntegration
from apps.atlas_agent.mailer import ColdMailer

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
    
    # 1. Scraper
    scraper = SchoolScraper(google_api_key=google_places_key)
    leads = scraper.run_pipeline(regions, queries)
    
    # 2. Enrichment
    enricher = EnrichmentService(api_key=apollo_key)
    enriched_leads = []
    for lead in leads:
        enriched = enricher.process_lead(lead)
        enriched_leads.append(enriched)
        
    # 3. Sheets Integration (Precisa do arquivo credentials.json na raiz do projeto)
    sheets_db = GoogleSheetsIntegration(spreadsheet_title="Planilha Matriz de Leads - Inteligência Comercial (PoC)")
    sheets_db.push_leads_batch(enriched_leads)
    
    # 4. Cold Mailing
    mailer = ColdMailer(smtp_user=smtp_user, smtp_pass=smtp_pass, dry_run=True)
    mailer.run_campaign(enriched_leads)
    
    # Backup CSV local
    csv_filename = "atlas_leads_mock.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Instituicao", "Tipo", "Cidade", "Regiao", "Nome_Decisor", 
            "Cargo", "Email", "Telefone", "Status", "Score", "Notas"
        ])
        for lead in enriched_leads:
            writer.writerow(lead.to_csv_row())
            
    print(f"--- Pipeline Concluido! {len(enriched_leads)} leads processados. ---")
    print(f"Salvo em: {csv_filename}")

if __name__ == "__main__":
    main()
