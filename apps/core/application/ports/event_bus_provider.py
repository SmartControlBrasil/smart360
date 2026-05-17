"""Port for resolving the process-wide EventBus without importing infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .event_bus import EventBus


class EventBusProvider(ABC):
    """Abstract access to the configured ``EventBus`` implementation."""

    @abstractmethod
    def get_event_bus(self) -> EventBus:
        """Return the shared ``EventBus`` instance for this runtime."""
