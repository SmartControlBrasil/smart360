"""Input payload for registering a new website project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateWebsiteProjectDto:
    """Identifiers and timestamps supplied by the caller (composition root / handler)."""

    project_id: UUID
    company_id: int
    name: str
    created_at: datetime
