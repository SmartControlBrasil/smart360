import requests
import urllib.parse
from typing import List, Optional
from .models import Lead

class SchoolScraper:
    """
    Motor base para varredura em lote por quadrantes estruturados.
    """
    def __init__(self, google_api_key: Optional[str] = None):
        self.google_api_key = google_api_key

    def search_schools_mock(self, query: str, region: str) -> List[Lead]:
        """
        Gera dados mockados de amostra para validação local antes de ativar APIs pagas.
        """
        print(f"[Atlas Scraper] Simulating search for: {query} in {region}")
        return [
            Lead(
                institution_name=f"Colégio {region} Inovação",
                city="São Paulo",
                region=region,
                website_domain=f"colegio{region.lower().replace(' ', '')}inovacao.com.br",
                phone="(11) 9999-0001",
            ),
            Lead(
                institution_name=f"Escola Particular Maker {region}",
                city="São Paulo",
                region=region,
                website_domain=f"escolamaker{region.lower().replace(' ', '')}.com.br",
                phone="(11) 9999-0002",
            )
        ]

    def search_google_places(self, query: str, region: str) -> List[Lead]:
        """
        Busca escolas usando Google Places API (Text Search).
        Requer google_api_key.
        """
        if not self.google_api_key:
            print("[Atlas Scraper] Warning: API Key missing. Returning Mock Data.")
            return self.search_schools_mock(query, region)
            
        full_query = f"{query} em {region}, São Paulo"
        encoded_query = urllib.parse.quote(full_query)
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={self.google_api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
            leads = []
            
            for result in data.get('results', []):
                name = result.get('name')
                address = result.get('formatted_address', '')
                
                # Fetch details for phone and website if needed (Place Details API)
                # This is a basic implementation
                leads.append(Lead(
                    institution_name=name,
                    city="São Paulo",
                    region=region,
                    notes=f"Endereço bruto: {address}"
                ))
            return leads
        except Exception as e:
            print(f"[Atlas Scraper] Error fetching from Places API: {str(e)}")
            return []

    def run_pipeline(self, regions: List[str], base_queries: List[str]) -> List[Lead]:
        """
        Executa a varredura completa.
        """
        all_leads = []
        for region in regions:
            for query in base_queries:
                print(f"[Atlas Scraper] Scanning {query} in {region}...")
                leads = self.search_google_places(query, region)
                all_leads.extend(leads)
        
        return all_leads
