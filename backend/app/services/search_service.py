"""Server-side scoped event search."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event


class CameraScopeError(ValueError):
    """Raised when a requested camera is not in the authorization scope."""


class OffsetFilterValidationError(ValueError):
    """Raised when recording-offset filters cannot be interpreted safely."""


class SearchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_events(
        self,
        allowed_camera_ids: list[str],
        camera_id: str | None = None,
        recording_id: str | None = None,
        event_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        start_offset_ms: int | None = None,
        end_offset_ms: int | None = None,
    ) -> list[Event]:
        if camera_id is not None and camera_id not in allowed_camera_ids:
            raise CameraScopeError("camera_id is outside the allowed camera scope")
        if (start_offset_ms is not None or end_offset_ms is not None) and recording_id is None:
            raise OffsetFilterValidationError(
                "recording_id is required when using offset filters",
            )
        if not allowed_camera_ids:
            return []

        statement = select(Event).where(Event.camera_id.in_(allowed_camera_ids))
        if camera_id is not None:
            statement = statement.where(Event.camera_id == camera_id)
        if recording_id is not None:
            statement = statement.where(Event.recording_id == recording_id)
        if event_type is not None:
            statement = statement.where(Event.event_type == event_type)
        if from_time is not None:
            statement = statement.where(Event.occurred_at >= from_time)
        if to_time is not None:
            statement = statement.where(Event.occurred_at <= to_time)
        if start_offset_ms is not None:
            statement = statement.where(Event.end_offset_ms >= start_offset_ms)
        if end_offset_ms is not None:
            statement = statement.where(Event.start_offset_ms <= end_offset_ms)

        return self.session.scalars(statement.order_by(Event.occurred_at, Event.id)).all()
