from __future__ import annotations

from datetime import datetime

from app.db import SessionLocal
from app.mcp.base import MCPTool
from app.models import Event
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway
from app.services.search_service import SearchService


def _event_data(event: Event) -> dict[str, object]:
    return {
        "id": event.id,
        "camera_id": event.camera_id,
        "recording_id": event.recording_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "description": event.description,
        "start_offset_ms": event.start_offset_ms,
        "end_offset_ms": event.end_offset_ms,
        "confidence": event.confidence,
        "snapshot_url": f"/api/v1/media/events/{event.id}/image" if event.snapshot_path or event.image_url else None,
        "clip_url": f"/api/v1/media/events/{event.id}/video" if event.clip_path or event.video_url else None,
    }


class SearchEventsTool(MCPTool):
    name = "search_events"
    description = "Search event metadata inside the authorized camera scope."
    required_permission = "event:search"

    def execute(self, context: SecurityContext, arguments: dict) -> list[dict[str, object]]:
        camera_id = arguments.get("camera_id")
        resource_type = "camera" if camera_id is not None else "event"
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "event:search",
                resource_type,
                str(camera_id) if camera_id is not None else None,
                lambda decision: [
                    _event_data(event)
                    for event in SearchService(session).search_events(
                        decision.allowed_camera_ids,
                        camera_id=str(camera_id) if camera_id is not None else None,
                        recording_id=_string_or_none(arguments.get("recording_id")),
                        event_type=_string_or_none(arguments.get("event_type")),
                        from_time=_datetime_or_none(arguments.get("from_time")),
                        to_time=_datetime_or_none(arguments.get("to_time")),
                        start_offset_ms=_int_or_none(arguments.get("start_offset_ms")),
                        end_offset_ms=_int_or_none(arguments.get("end_offset_ms")),
                    )
                ],
            )


def _string_or_none(value: object) -> str | None:
    return str(value) if value is not None else None


def _int_or_none(value: object) -> int | None:
    return int(value) if value is not None else None


def _datetime_or_none(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
