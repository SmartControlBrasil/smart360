"""Smart Site Factory domain events (lifecycle facts, framework-agnostic).

When publishing to the platform bus, map instances to
``apps.core.domain.events.DomainEvent`` (stable ``event_name`` + ``payload``)
in an adapter — not in this layer.
"""

from .briefing_submitted import BriefingSubmitted
from .project_created import ProjectCreated
from .project_status_changed import ProjectStatusChanged

__all__ = [
    "BriefingSubmitted",
    "ProjectCreated",
    "ProjectStatusChanged",
]
