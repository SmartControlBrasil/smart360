"""Input payload for recording a submitted project briefing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SubmitProjectBriefDto:
    """Brief content and scope ids; persistence and clock are orchestrated outside."""

    brief_id: UUID
    project_id: UUID
    company_id: int
    answers: dict[str, object]
    created_at: datetime
