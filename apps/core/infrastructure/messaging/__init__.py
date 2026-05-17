"""Infrastructure adapters for domain event delivery."""

from .in_memory_event_bus import InMemoryEventBus

__all__ = ["InMemoryEventBus"]
