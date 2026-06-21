import requests
from typing import Optional
from .models import Lead

class EnrichmentService:
    """
    Serviço para buscar tomadores de decisão (Diretor, Mantenedor, etc) 
    usando APIs de B2B Data (ex: Apollo.io, Hunter.io, Lusha).
    """
    def __init__(self, api_key: Optional[str] = None, provider: str = "apollo"):
        self.api_key = api_key
        self.provider = provider
        
    def enrich_mock(self, lead: Lead) -> Lead:
        """
        Mock data for local validation pipeline.
        """
        print(f"[Atlas Enricher] Simulating enrichment for domain: {lead.website_domain}")
        lead.decider_name = "João Silva"
        lead.decider_role = "Diretor Pedagógico"
        if lead.website_domain:
            lead.contact_email = f"diretoria@{lead.website_domain}"
        else:
            lead.contact_email = "contato@escola.com.br"
        
        # Filtro de Scoring: Escola rica em dados, damos score 5.
        lead.lead_score = 5
        return lead

    def enrich_apollo(self, lead: Lead) -> Lead:
        """
        Integração com Apollo.io API (People Search)
        """
        if not self.api_key:
            print("[Atlas Enricher] Warning: API Key missing. Returning Mock Data.")
            return self.enrich_mock(lead)
            
        if not lead.website_domain:
            print(f"[Atlas Enricher] No domain to enrich for {lead.institution_name}")
            return lead
            
        url = "https://api.apollo.io/v1/mixed_people/search"
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json"
        }
        
        # Busca por cargos de diretoria ou coordenação
        data = {
            "api_key": self.api_key,
            "q_organization_domains": lead.website_domain,
            "person_titles": ["diretor", "mantenedor", "coordenador", "secretario"],
            "page": 1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            results = response.json()
            
            if results.get('people') and len(results['people']) > 0:
                person = results['people'][0]
                lead.decider_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                lead.decider_role = person.get('title', '')
                lead.contact_email = person.get('email', '')
                lead.lead_score = 5 if lead.contact_email else 3
            else:
                print(f"[Atlas Enricher] No people found for {lead.website_domain}")
                
        except Exception as e:
            print(f"[Atlas Enricher] Error querying Apollo: {str(e)}")
            
        return lead

    def process_lead(self, lead: Lead) -> Lead:
        """
        Função principal do microsserviço de enriquecimento.
        """
        if self.provider == "apollo":
            return self.enrich_apollo(lead)
        else:
            return self.enrich_mock(lead)
