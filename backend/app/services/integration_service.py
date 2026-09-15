"""Minimal resource integration facade; real video ingestion arrives later."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Camera, Event


class IntegrationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load_event(self, event_id: str) -> Event | None:
        return self.session.get(Event, event_id)

    def load_image(self, event_id: str) -> dict[str, object]:
        event = self.load_event(event_id)
        if event is None:
            return {"event_id": event_id, "url": None, "is_mock": True}
        return {
            "event_id": event.id,
            "url": event.snapshot_path or event.image_url or f"mock://events/{event.id}/image",
            "is_mock": event.snapshot_path is None and event.image_url is None,
        }

    def load_video(self, event_id: str) -> dict[str, object]:
        event = self.load_event(event_id)
        if event is None:
            return {"event_id": event_id, "url": None, "is_mock": True}
        return {
            "event_id": event.id,
            "url": event.clip_path or event.video_url or f"mock://events/{event.id}/video",
            "is_mock": event.clip_path is None and event.video_url is None,
        }

    def load_live(self, camera_id: str) -> dict[str, object]:
        camera = self.session.get(Camera, camera_id)
        if camera is None:
            return {"camera_id": camera_id, "url": None, "is_mock": True}
        return {
            "camera_id": camera.id,
            "url": f"mock://cameras/{camera.id}/live",
            "is_mock": True,
        }
