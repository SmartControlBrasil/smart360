"""Website production project aggregate root (factory-facing shape)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..value_objects.project_status import ProjectStatus


@dataclass
class WebsiteProject:
    """
    A site build scoped to a company, tracked by name and workflow status.

    Persistence and Django models live outside this layer; ids are domain identifiers.
    """

    id: UUID
    company_id: int
    name: str
    status: ProjectStatus
    created_at: datetime
