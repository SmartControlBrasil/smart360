"""Outbound persistence port for ``ProjectBrief`` records."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ...domain.entities.project_brief import ProjectBrief


class ProjectBriefRepository(Protocol):
    """Load and persist project briefs."""

    def save(self, brief: ProjectBrief) -> None:
        """Insert or update the given brief."""

    def get_by_project_id(self, project_id: UUID) -> ProjectBrief | None:
        """Return a brief linked to the project, if present."""
