from __future__ import annotations

from app.event_bus.memory import InMemoryEventBus


class MonitorService:
    """Small local observer retained for demo visibility of IVA event publication."""

    def __init__(self, event_bus: InMemoryEventBus) -> None:
        self.published_events: list[dict[str, object]] = []
        event_bus.subscribe("iva.events", self.published_events.append)
