"""Use case: create a website project and announce it on the platform event bus."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from apps.core.application.ports.event_bus import EventBus
from apps.core.domain.events.domain_event import DomainEvent

from ...domain.entities.website_project import WebsiteProject
from ...domain.events.project_created import ProjectCreated
from ...domain.value_objects.project_status import ProjectStatus
from ..dtos.create_website_project_dto import CreateWebsiteProjectDto
from ..ports.website_project_repository import WebsiteProjectRepository

_EVENT_NAME = "smart_site_factory.project.created"


def _domain_event_from_project_created(fact: ProjectCreated, occurred_at: datetime) -> DomainEvent:
    return DomainEvent(
        event_id=uuid4(),
        event_name=_EVENT_NAME,
        occurred_at=occurred_at,
        aggregate_id=str(fact.project_id),
        aggregate_type="WebsiteProject",
        payload={
            "project_id": str(fact.project_id),
            "company_id": fact.company_id,
            "project_name": fact.project_name,
        },
    )


class CreateWebsiteProject:
    """Persist a new aggregate and publish the corresponding lifecycle fact."""

    def __init__(
        self,
        projects: WebsiteProjectRepository,
        event_bus: EventBus,
    ) -> None:
        self._projects = projects
        self._event_bus = event_bus

    def execute(self, dto: CreateWebsiteProjectDto) -> WebsiteProject:
        project = WebsiteProject(
            id=dto.project_id,
            company_id=dto.company_id,
            name=dto.name,
            status=ProjectStatus.BRIEFING_PENDING,
            created_at=dto.created_at,
        )
        self._projects.save(project)
        fact = ProjectCreated(
            project_id=project.id,
            company_id=project.company_id,
            project_name=project.name,
        )
        self._event_bus.publish(_domain_event_from_project_created(fact, dto.created_at))
        return project
