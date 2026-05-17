"""
Outbound port for publishing domain events to the platform Integration Bus.

Implementations live in infrastructure (e.g. Celery, Redis streams, outbox table).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ...domain.events.domain_event import DomainEvent


class EventBus(ABC):
    """Abstract event publisher — no transport or Django specifics."""

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Emit a single domain event to subscribers."""

    @abstractmethod
    def publish_many(self, events: Iterable[DomainEvent]) -> None:
        """Emit multiple events atomically if the adapter supports it; otherwise loop."""
