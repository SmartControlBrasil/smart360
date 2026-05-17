"""Structured briefing answers captured for a website project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ProjectBrief:
    """
    Questionnaire responses keyed by question slug (or similar), tied to one project.

    ``answers`` is intentionally unstructured at this stage; adapters interpret keys.
    """

    id: UUID
    project_id: UUID
    answers: dict[str, object]
    created_at: datetime
