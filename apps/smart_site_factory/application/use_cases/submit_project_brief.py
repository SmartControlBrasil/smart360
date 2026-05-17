"""Use case: persist a briefing and announce ``BriefingSubmitted`` on the event bus."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from apps.core.application.ports.event_bus import EventBus
from apps.core.domain.events.domain_event import DomainEvent

from ...domain.entities.project_brief import ProjectBrief
from ...domain.events.briefing_submitted import BriefingSubmitted
from ..dtos.submit_project_brief_dto import SubmitProjectBriefDto
from ..ports.project_brief_repository import ProjectBriefRepository

_EVENT_NAME = "smart_site_factory.briefing.submitted"


def _domain_event_from_briefing_submitted(fact: BriefingSubmitted, occurred_at: datetime) -> DomainEvent:
    return DomainEvent(
        event_id=uuid4(),
        event_name=_EVENT_NAME,
        occurred_at=occurred_at,
        aggregate_id=str(fact.project_id),
        aggregate_type="WebsiteProject",
        payload={
            "project_id": str(fact.project_id),
            "brief_id": str(fact.brief_id),
            "company_id": fact.company_id,
        },
    )


class SubmitProjectBrief:
    """Save questionnaire answers and publish the submission fact."""

    def __init__(
        self,
        briefs: ProjectBriefRepository,
        event_bus: EventBus,
    ) -> None:
        self._briefs = briefs
        self._event_bus = event_bus

    def execute(self, dto: SubmitProjectBriefDto) -> ProjectBrief:
        brief = ProjectBrief(
            id=dto.brief_id,
            project_id=dto.project_id,
            answers=dict(dto.answers),
            created_at=dto.created_at,
        )
        self._briefs.save(brief)
        fact = BriefingSubmitted(
            project_id=brief.project_id,
            brief_id=brief.id,
            company_id=dto.company_id,
        )
        self._event_bus.publish(_domain_event_from_briefing_submitted(fact, dto.created_at))
        return brief
