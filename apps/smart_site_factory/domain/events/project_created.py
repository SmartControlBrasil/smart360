"""Emitted when a new website project is registered in the factory."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProjectCreated:
    """Fact: a ``WebsiteProject`` was created for a company under a display name."""

    project_id: UUID
    company_id: int
    project_name: str
