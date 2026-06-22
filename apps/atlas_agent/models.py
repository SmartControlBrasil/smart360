from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Lead:
    institution_name: str
    city: str
    region: str
    website_domain: Optional[str] = None
    phone: Optional[str] = None
    decider_name: Optional[str] = None
    decider_role: Optional[str] = None
    contact_email: Optional[str] = None
    institution_type: str = "Privada"
    approach_status: str = "Pendente"
    lead_score: int = 0
    segment: str = "Outros"
    notes: str = ""

    def to_csv_row(self) -> List[str]:
        return [
            self.institution_name,
            self.institution_type,
            self.city,
            self.region,
            self.decider_name or "",
            self.decider_role or "",
            self.contact_email or "",
            self.phone or "",
            self.approach_status,
            str(self.lead_score),
            self.notes or ""
        ]
