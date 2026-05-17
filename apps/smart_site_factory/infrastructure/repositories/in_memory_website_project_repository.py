"""In-memory ``WebsiteProjectRepository`` for local development and tests."""

from __future__ import annotations

from threading import Lock
from uuid import UUID

from ...domain.entities.website_project import WebsiteProject


class InMemoryWebsiteProjectRepository:
    """
    Thread-safe dict keyed by project id.

    Data is lost when the process exits; use Django-backed adapters in production.
    """

    def __init__(self) -> None:
        self._by_id: dict[UUID, WebsiteProject] = {}
        self._lock = Lock()

    def save(self, project: WebsiteProject) -> None:
        with self._lock:
            self._by_id[project.id] = project

    def get_by_id(self, project_id: UUID) -> WebsiteProject | None:
        with self._lock:
            return self._by_id.get(project_id)

    def list_by_company(self, company_id: int) -> list[WebsiteProject]:
        with self._lock:
            return [p for p in self._by_id.values() if p.company_id == company_id]
