"""Emitted when a project briefing (questionnaire) is submitted."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class BriefingSubmitted:
    """Fact: a ``ProjectBrief`` was recorded for a project under a company scope."""

    project_id: UUID
    brief_id: UUID
    company_id: int
