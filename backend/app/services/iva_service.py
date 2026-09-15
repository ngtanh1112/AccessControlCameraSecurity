"""Recording ingestion and synchronous local IVA orchestration."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.event_bus.memory import InMemoryEventBus
from app.models import Camera, Event, VideoAnalysisStatus, VideoRecording
from app.services.media_storage import MediaStorage
from app.services.video_analyzer import DetectedEvent, VideoAnalyzer


class IVAService:
    def __init__(
        self,
        session: Session,
        analyzer: VideoAnalyzer,
        storage: MediaStorage,
        event_bus: InMemoryEventBus | None = None,
    ) -> None:
        self.session = session
        self.analyzer = analyzer
        self.storage = storage
        self.event_bus = event_bus or InMemoryEventBus()
        self.event_bus.subscribe("iva.events", self._persist_event)

    def create_recording(
        self,
        *,
        camera_id: str,
        original_filename: str,
        upload_path: Path,
        recording_started_at: datetime,
    ) -> VideoRecording:
        if self.session.get(Camera, camera_id) is None:
            raise LookupError("Camera not found")
        recording_id = f"REC-{uuid4().hex[:16].upper()}"
        recording = VideoRecording(
            id=recording_id,
            camera_id=camera_id,
            original_filename=original_filename,
            stored_path=self.storage.save_upload(recording_id, upload_path),
            recording_started_at=recording_started_at,
            duration_ms=None,
            analysis_status=VideoAnalysisStatus.PENDING,
            analyzed_at=None,
            model_name=None,
        )
        self.session.add(recording)
        self.session.commit()
        return recording

    def analyze_recording(self, recording_id: str) -> tuple[VideoRecording, list[Event]]:
        recording = self.session.get(VideoRecording, recording_id)
        if recording is None:
            raise LookupError("Recording not found")
        recording.analysis_status = VideoAnalysisStatus.ANALYZING
        self.session.commit()
        try:
            detected_events = self.analyzer.analyze(recording)
            persisted_events: list[Event] = []
            for index, detected in enumerate(detected_events, start=1):
                event_id = self._event_id(recording, index)
                snapshot_path = self.storage.save_snapshot(event_id, detected.best_frame)
                clip_path = self.storage.create_clip(
                    event_id=event_id,
                    recording_path=recording.stored_path,
                    start_offset_ms=detected.start_offset_ms,
                    end_offset_ms=detected.end_offset_ms,
                    duration_ms=recording.duration_ms,
                    padding_seconds=float(os.getenv("CLIP_PADDING_SECONDS", "2.0")),
                )
                payload = self._event_payload(recording, event_id, detected, snapshot_path, clip_path)
                self.event_bus.publish("iva.events", payload)
                self.session.flush()
                event = self.session.get(Event, event_id)
                if event is not None:
                    persisted_events.append(event)
            recording.analysis_status = VideoAnalysisStatus.COMPLETED
            recording.analyzed_at = datetime.utcnow()
            recording.model_name = getattr(self.analyzer, "model_name", self.analyzer.__class__.__name__)
            self.session.commit()
            return recording, persisted_events
        except Exception:
            self.session.rollback()
            failed_recording = self.session.get(VideoRecording, recording_id)
            if failed_recording is not None:
                failed_recording.analysis_status = VideoAnalysisStatus.FAILED
                failed_recording.analyzed_at = datetime.utcnow()
                self.session.commit()
            raise

    @staticmethod
    def _event_id(recording: VideoRecording, index: int) -> str:
        camera = recording.camera_id.replace("CAM-", "")
        return f"EVT-{camera}-{recording.id[-8:]}-{index:03d}"

    @staticmethod
    def _event_payload(
        recording: VideoRecording,
        event_id: str,
        detected: DetectedEvent,
        snapshot_path: str | None,
        clip_path: str | None,
    ) -> dict[str, object]:
        return {
            "event_id": event_id,
            "recording_id": recording.id,
            "camera_id": recording.camera_id,
            "event_type": detected.event_type,
            "occurred_at": recording.recording_started_at + timedelta(milliseconds=detected.start_offset_ms),
            "start_offset_ms": detected.start_offset_ms,
            "end_offset_ms": detected.end_offset_ms,
            "confidence": detected.confidence,
            "snapshot_path": snapshot_path,
            "clip_path": clip_path,
        }

    def _persist_event(self, payload: dict[str, object]) -> None:
        event_id = str(payload["event_id"])
        if self.session.get(Event, event_id) is not None:
            return
        self.session.add(
            Event(
                id=event_id,
                recording_id=str(payload["recording_id"]),
                camera_id=str(payload["camera_id"]),
                event_type=str(payload["event_type"]),
                occurred_at=payload["occurred_at"],  # type: ignore[arg-type]
                description=f"IVA {payload['event_type']} from recording {payload['recording_id']}",
                start_offset_ms=int(payload["start_offset_ms"]),
                end_offset_ms=int(payload["end_offset_ms"]),
                confidence=float(payload["confidence"]),
                snapshot_path=payload["snapshot_path"],  # type: ignore[arg-type]
                clip_path=payload["clip_path"],  # type: ignore[arg-type]
                image_url=None,
                video_url=None,
            ),
        )
