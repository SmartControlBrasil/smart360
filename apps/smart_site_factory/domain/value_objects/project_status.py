"""Lifecycle states for a website production project in Smart Site Factory."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    """Where the project sits in the factory workflow (briefing → delivery)."""

    BRIEFING_PENDING = "briefing_pending"
    IN_PRODUCTION = "in_production"
    WAITING_APPROVAL = "waiting_approval"
    DELIVERED = "delivered"
