"""In-memory ``ProjectBriefRepository`` for local development and tests."""

from __future__ import annotations

from threading import Lock
from uuid import UUID

from ...domain.entities.project_brief import ProjectBrief


class InMemoryProjectBriefRepository:
    """
    Thread-safe store keyed by ``project_id`` (one brief slot per project).

    ``save`` replaces any previous brief for the same project. Not durable across processes;
    production code should use a Django ORM adapter under ``infrastructure/repositories/``.
    """

    def __init__(self) -> None:
        self._by_project_id: dict[UUID, ProjectBrief] = {}
        self._lock = Lock()

    def save(self, brief: ProjectBrief) -> None:
        with self._lock:
            self._by_project_id[brief.project_id] = brief

    def get_by_project_id(self, project_id: UUID) -> ProjectBrief | None:
        with self._lock:
            return self._by_project_id.get(project_id)
