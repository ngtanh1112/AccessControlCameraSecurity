from __future__ import annotations

from collections import defaultdict

from app.event_bus.base import EventHandler


class InMemoryEventBus:
    """Synchronous local bus; suitable for a single-process POC only."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._handlers[topic].append(handler)

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        for handler in self._handlers[topic]:
            handler(payload)
