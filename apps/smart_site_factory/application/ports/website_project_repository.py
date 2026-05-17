"""Outbound persistence port for ``WebsiteProject`` aggregates."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ...domain.entities.website_project import WebsiteProject


class WebsiteProjectRepository(Protocol):
    """Load and persist website projects without ORM or framework details."""

    def save(self, project: WebsiteProject) -> None:
        """Insert or update the given aggregate."""

    def get_by_id(self, project_id: UUID) -> WebsiteProject | None:
        """Return the project if it exists; otherwise ``None``."""

    def list_by_company(self, company_id: int) -> list[WebsiteProject]:
        """Return all projects for the company (empty list if none)."""
