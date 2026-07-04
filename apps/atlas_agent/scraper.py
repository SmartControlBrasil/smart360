import requests
import urllib.parse
import os
from typing import List, Optional
from .models import Lead

class SchoolScraper:
    """
    Motor base para varredura em lote por quadrantes estruturados.
    """
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        production: bool = False,
        source: str = "mock",
        mock_csv_path: Optional[str] = None,
    ):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self.production = production
        self.source = (source or "mock").strip().lower()
        self.mock_csv_path = mock_csv_path
        self.collected_count = 0
        self.limited_count = 0
        self.error_count = 0

    def search_schools_mock(self, query: str, region: str, mock_csv_path: Optional[str] = None) -> List[Lead]:
        """
        Gera dados mockados de amostra para validação local antes de ativar APIs pagas.
        """
        print(f"[Atlas Scraper] Simulating search for: {query} in {region}")
        from pathlib import Path
        from apps.atlas_agent.config import AtlasConfigError
        import csv
        
        target_path = mock_csv_path or self.mock_csv_path
        resolved_path = None
        
        if target_path:
            resolved_path = Path(target_path)
            if not resolved_path.is_absolute():
                resolved_path = (Path(__file__).resolve().parent / resolved_path).resolve()

        if resolved_path:
            try:
                leads = []
                with open(resolved_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_lower = {k.lower(): v for k, v in row.items()}
                        name = row_lower.get("instituicao") or row_lower.get("company_name") or row_lower.get("name") or "Escola Mock"
                        city = row_lower.get("cidade") or row_lower.get("city") or "São Paulo"
                        reg = row_lower.get("regiao") or row_lower.get("region") or region
                        website = row_lower.get("website") or ""
                        phone = row_lower.get("telefone") or row_lower.get("phone") or ""
                        email = row_lower.get("email") or ""
                        decider_name = row_lower.get("nome_decisor") or row_lower.get("decider_name") or ""
                        decider_role = row_lower.get("cargo") or row_lower.get("decider_role") or ""
                        notes = row_lower.get("notas") or row_lower.get("notes") or ""
                        
                        leads.append(Lead(
                            institution_name=name,
                            city=city,
                            region=reg,
                            website_domain=website,
                            phone=phone,
                            contact_email=email,
                            decider_name=decider_name,
                            decider_role=decider_role,
                            notes=notes
                        ))
                print(f"[Atlas Scraper] {len(leads)} leads lidos com sucesso do CSV mock em: {resolved_path}")
                return leads
            except (OSError, PermissionError) as exc:
                raise AtlasConfigError("Arquivo mock indisponível ou sem permissão") from exc
        
        print(f"[Atlas Scraper] Usando fallback de dados mockados estáticos.")
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
        if self.source != "google_places":
            print("[Atlas Scraper] fonte mock ativa (ATLAS_SOURCE=mock).")
            return self.search_schools_mock(query, region, self.mock_csv_path)

        if not self.google_api_key:
            print("[Atlas Scraper] fallback para mock: chave Google Places ausente.")
            return self.search_schools_mock(query, region, self.mock_csv_path)

        full_query = f"{query} em {region}, São Paulo"
        encoded_query = urllib.parse.quote(full_query)
        print(f"[Atlas Scraper] fonte Google Places real ativa para query='{query}' regiao='{region}'.")
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={self.google_api_key}"

        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
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
            print(f"[Atlas Scraper] falha no Google Places ({str(e)}). fallback para mock.")
            return self.search_schools_mock(query, region, self.mock_csv_path)

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
