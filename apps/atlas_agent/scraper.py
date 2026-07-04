import requests
import urllib.parse
import os
from typing import List, Optional
from .models import Lead

class SchoolScraper:
    """
    Motor base para varredura em lote por quadrantes estruturados.
    """
    def __init__(self, google_api_key: Optional[str] = None, production: bool = False):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self.production = production
        self.collected_count = 0
        self.limited_count = 0
        self.error_count = 0

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
        if not self.production:
            print("[Atlas Scraper] Scraper is in mock mode (not production). Returning Mock Data.")
            return self.search_schools_mock(query, region)

        if not self.google_api_key:
            raise ValueError("[Atlas Scraper] Erro: Chave do Google Places ausente em production.")

        full_query = f"{query} em {region}, São Paulo"
        encoded_query = urllib.parse.quote(full_query)
        print(f"[Atlas Scraper] Searching Google Places for: {query} in {region}...")
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={self.google_api_key}"

        try:
            response = requests.get(url)
            data = response.json()
            leads = []

            for result in data.get('results', []):
                name = result.get('name')
                address = result.get('formatted_address', '')

                leads.append(Lead(
                    institution_name=name,
                    city="São Paulo",
                    region=region,
                    notes=f"Endereço bruto: {address}"
                ))
            return leads
        except Exception as e:
            self.error_count += 1
            print(f"[Atlas Scraper] Error fetching from Places API: {str(e)}")
            return []

    def run_pipeline(self, regions: List[str], base_queries: List[str], max_results: int = 10) -> List[Lead]:
        """
        Executa a varredura completa.
        """
        self.collected_count = 0
        self.limited_count = 0
        self.error_count = 0
        all_leads = []

        for region in regions:
            for query in base_queries:
                if len(all_leads) >= max_results:
                    break
                print(f"[Atlas Scraper] Scanning {query} in {region}...")
                leads = self.search_google_places(query, region)
                self.collected_count += len(leads)
                all_leads.extend(leads)

        if len(all_leads) > max_results:
            self.limited_count = len(all_leads) - max_results
            all_leads = all_leads[:max_results]

        return all_leads
