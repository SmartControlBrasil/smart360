"""Default Core wiring: single in-memory bus for dev/tests (no Django settings)."""

from __future__ import annotations

from ...application.ports.event_bus import EventBus
from ...application.ports.event_bus_provider import EventBusProvider
from .in_memory_event_bus import InMemoryEventBus

_singleton: InMemoryEventBus = InMemoryEventBus()


def get_event_bus() -> EventBus:
    """Return the shared in-memory ``EventBus`` singleton."""
    return _singleton


class InMemoryEventBusProvider(EventBusProvider):
    """``EventBusProvider`` backed by the module singleton."""

    def get_event_bus(self) -> EventBus:
        return get_event_bus()
