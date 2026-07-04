from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import requests

from .models import Lead


ATLAS_IMPORT_PATH = "/api/v1/ai-agents/atlas/import-prospects/"
DEFAULT_MIN_SCORE = 5


def qualified_prospects(leads: Iterable[Lead], minimum_score: int = DEFAULT_MIN_SCORE) -> list[Lead]:
    return [lead for lead in leads if lead.lead_score >= minimum_score]


def prospect_to_api_row(lead: Lead) -> dict[str, str]:
    website = (lead.website_domain or "").strip()
    if website and not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    score_note = f"Score de qualificacao Atlas PoC: {lead.lead_score}/10."
    region_note = f" Regiao pesquisada: {lead.region}." if lead.region else ""
    original_notes = f" {lead.notes.strip()}" if lead.notes and lead.notes.strip() else ""

    return {
        "company_name": lead.institution_name,
        "segment": lead.institution_type or "Educacao",
        "city": lead.city,
        "state": "SP" if lead.city.lower() == "sao paulo" or lead.city.lower() == "são paulo" else "",
        "website": website,
        "contact_email": lead.contact_email or "",
        "contact_phone": lead.phone or "",
        "contact_name": lead.decider_name or "",
        "notes": f"{score_note}{region_note}{original_notes}".strip(),
        "source": "google_maps",
    }


@dataclass
class AtlasImportResult:
    public_id: str
    status: str
    processed_rows: int
    created_opportunities: int
    skipped_duplicates: int
    errors: list[dict]


class AtlasAPIClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        company_id: int,
        timeout: int = 30,
        session=None,
    ):
        if not base_url.strip():
            raise ValueError("ATLAS_API_BASE_URL precisa ser configurada.")
        if not token.strip():
            raise ValueError("ATLAS_API_TOKEN precisa ser configurado.")
        if company_id <= 0:
            raise ValueError("ATLAS_COMPANY_ID precisa ser um inteiro positivo.")

        self.endpoint = urljoin(base_url.rstrip("/") + "/", ATLAS_IMPORT_PATH.lstrip("/"))
        self.token = token.strip()
        self.company_id = company_id
        self.timeout = timeout
        self.session = session or requests.Session()

    def import_prospects(self, leads: Iterable[Lead], *, filename: str = "atlas-agent-poc.json") -> AtlasImportResult:
        rows = [prospect_to_api_row(lead) for lead in leads]
        if not rows:
            raise ValueError("Nenhum prospect qualificado para importar.")

        response = self.session.post(
            self.endpoint,
            json={
                "company": self.company_id,
                "source": "google_maps",
                "filename": filename,
                "rows": rows,
            },
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return AtlasImportResult(
            public_id=str(payload.get("public_id") or ""),
            status=str(payload.get("status") or ""),
            processed_rows=int(payload.get("processed_rows") or 0),
            created_opportunities=int(payload.get("created_opportunities") or 0),
            skipped_duplicates=int(payload.get("skipped_duplicates") or 0),
            errors=list(payload.get("errors") or []),
        )
