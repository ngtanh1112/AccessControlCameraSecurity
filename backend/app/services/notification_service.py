"""Minimal in-memory notification storage for authorized camera alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


class NotificationService:
    """Stores alert notifications for the lifetime of the local application process."""

    def __init__(self) -> None:
        self._notifications: list[dict[str, str]] = []

    def create_alert(self, *, camera_id: str, message: str, created_by: str) -> dict[str, str]:
        notification = {
            "id": str(uuid4()),
            "camera_id": camera_id,
            "message": message,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._notifications.append(notification)
        return notification

    def list_notifications(self) -> list[dict[str, str]]:
        """Return a copy so callers cannot mutate the service's stored alerts."""
        return list(self._notifications)
