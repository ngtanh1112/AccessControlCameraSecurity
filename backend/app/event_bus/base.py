from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


EventHandler = Callable[[dict[str, object]], None]


class EventBus(Protocol):
    def publish(self, topic: str, payload: dict[str, object]) -> None: ...

    def subscribe(self, topic: str, handler: EventHandler) -> None: ...
