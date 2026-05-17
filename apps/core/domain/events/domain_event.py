"""
Framework-agnostic base type for domain events published across Smart360.

Events are facts about something that already happened in a bounded context.
Infrastructure adapters serialize these for the Integration Bus / message broker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """
    Canonical envelope for cross-cutting propagation (notifications, analytics, etc.).

    Attributes:
        event_id: Unique idempotency key for this occurrence (often UUID v4).
        event_name: Stable string identifier, e.g. ``smart360.core.service_contract.activated``.
        occurred_at: When the fact happened (timezone-aware recommended).
        aggregate_id: Stable identifier of the aggregate root instance (string for flexibility).
        aggregate_type: Logical aggregate name, e.g. ``ServiceContract``, ``CompanyProductRelation``.
        payload: Domain-specific primitive data for subscribers (schemas versioned separately).
        metadata: Cross-cutting context (correlation_id, causation_id, actor_user_id, tenant hints).
    """

    event_id: UUID
    event_name: str
    occurred_at: datetime
    aggregate_id: str
    aggregate_type: str
    payload: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)
