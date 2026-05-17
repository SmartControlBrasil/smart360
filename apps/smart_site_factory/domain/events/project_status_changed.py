"""Emitted when a project moves to another step in the factory workflow."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ..value_objects.project_status import ProjectStatus


@dataclass(frozen=True)
class ProjectStatusChanged:
    """Fact: a ``WebsiteProject`` transitioned from one ``ProjectStatus`` to another."""

    project_id: UUID
    company_id: int
    old_status: ProjectStatus
    new_status: ProjectStatus
