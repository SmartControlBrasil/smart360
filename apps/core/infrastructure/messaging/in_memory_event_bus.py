"""
In-process EventBus for local development, tests, and debugging.

Not suitable for production fan-out: events are lost on process exit and are
not visible to other workers or services.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from threading import Lock
from typing import Any

from ...application.ports.event_bus import EventBus
from ...domain.events.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBus):
    """
    Append-only in-memory bus with optional structured logging of ``event_name``.

    Thread-safe for concurrent ``publish`` / ``publish_many`` calls.
    """

    def __init__(self, *, log_event_names: bool = True) -> None:
        self._log_event_names = log_event_names
        self._published: list[DomainEvent] = []
        self._lock = Lock()

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            self._published.append(event)
        self._maybe_log(event)

    def publish_many(self, events: Iterable[DomainEvent]) -> None:
        batch = list(events)
        with self._lock:
            self._published.extend(batch)
        for event in batch:
            self._maybe_log(event)

    def snapshot(self) -> tuple[DomainEvent, ...]:
        """Return an immutable copy of all events published so far (newest last)."""
        with self._lock:
            return tuple(self._published)

    def clear(self) -> None:
        """Drop stored events (intended for tests / dev resets only)."""
        with self._lock:
            self._published.clear()

    def _maybe_log(self, event: DomainEvent) -> None:
        if not self._log_event_names:
            return
        logger.info(
            "Published domain event: %s",
            event.event_name,
            extra=self._log_extra(event),
        )

    @staticmethod
    def _log_extra(event: DomainEvent) -> dict[str, Any]:
        return {
            "event_id": str(event.event_id),
            "event_name": event.event_name,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
        }
