"""Admin-only local video ingestion and analysis APIs."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.event_bus.memory import InMemoryEventBus
from app.models import Camera, Event, RoleName, VideoRecording
from app.security.context import SecurityContext, get_security_context
from app.services.iva_service import IVAService
from app.services.media_storage import MediaStorage
from app.services.video_analyzer import create_video_analyzer


router = APIRouter(prefix="/api/v1/iva", tags=["iva"])


def _require_admin(context: SecurityContext) -> None:
    if context.role != RoleName.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource.")


def _recording_data(recording: VideoRecording) -> dict[str, object]:
    return {
        "recording_id": recording.id,
        "camera_id": recording.camera_id,
        "original_filename": recording.original_filename,
        "recording_started_at": recording.recording_started_at,
        "duration_ms": recording.duration_ms,
        "status": recording.analysis_status.value,
        "analyzed_at": recording.analyzed_at,
        "model_name": recording.model_name,
    }


def _event_data(event: Event) -> dict[str, object]:
    return {
        "event_id": event.id,
        "recording_id": event.recording_id,
        "camera_id": event.camera_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "start_offset_ms": event.start_offset_ms,
        "end_offset_ms": event.end_offset_ms,
        "confidence": event.confidence,
        "snapshot_url": f"/api/v1/media/events/{event.id}/image" if event.snapshot_path else None,
        "clip_url": f"/api/v1/media/events/{event.id}/video" if event.clip_path else None,
    }


def _service(session: Session) -> IVAService:
    return IVAService(session, create_video_analyzer(), MediaStorage(), InMemoryEventBus())


@router.post("/recordings")
async def upload_recording(
    camera_id: str = Form(),
    recording_started_at: datetime = Form(),
    file: UploadFile = File(),
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    _require_admin(context)
    if Path(file.filename or "").suffix.casefold() != ".mp4":
        raise HTTPException(status_code=422, detail="Only .mp4 video uploads are accepted.")
    camera = session.get(Camera, camera_id)
    if camera is None or camera.organization_id != context.organization_id:
        raise HTTPException(status_code=404, detail="Camera not found")
    with NamedTemporaryFile(suffix=".mp4", delete=False) as temporary:
        temporary_path = Path(temporary.name)
        shutil.copyfileobj(file.file, temporary)
    try:
        recording = _service(session).create_recording(
            camera_id=camera_id,
            original_filename=file.filename or "recording.mp4",
            upload_path=temporary_path,
            recording_started_at=recording_started_at,
        )
    finally:
        await file.close()
        temporary_path.unlink(missing_ok=True)
    return {"recording_id": recording.id, "camera_id": recording.camera_id, "status": recording.analysis_status.value}


@router.post("/recordings/{recording_id}/analyze")
def analyze_recording(
    recording_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    _require_admin(context)
    recording = session.get(VideoRecording, recording_id)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    camera = session.get(Camera, recording.camera_id)
    if camera is None or camera.organization_id != context.organization_id:
        raise HTTPException(status_code=404, detail="Recording not found")
    try:
        recording, events = _service(session).analyze_recording(recording_id)
    except Exception as error:
        raise HTTPException(status_code=500, detail="Video analysis failed") from error
    return {**_recording_data(recording), "events": [_event_data(event) for event in events]}


@router.get("/recordings")
def list_recordings(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    _require_admin(context)
    return [
        _recording_data(recording)
        for recording in session.scalars(
            select(VideoRecording).join(Camera).where(Camera.organization_id == context.organization_id).order_by(VideoRecording.created_at.desc()),
        ).all()
    ]


@router.get("/recordings/{recording_id}")
def get_recording(
    recording_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    _require_admin(context)
    recording = session.get(VideoRecording, recording_id)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    camera = session.get(Camera, recording.camera_id)
    if camera is None or camera.organization_id != context.organization_id:
        raise HTTPException(status_code=404, detail="Recording not found")
    return _recording_data(recording)


@router.get("/recordings/{recording_id}/events")
def list_recording_events(
    recording_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    _require_admin(context)
    recording = session.get(VideoRecording, recording_id)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    camera = session.get(Camera, recording.camera_id)
    if camera is None or camera.organization_id != context.organization_id:
        raise HTTPException(status_code=404, detail="Recording not found")
    return [_event_data(event) for event in session.scalars(select(Event).where(Event.recording_id == recording_id).order_by(Event.start_offset_ms, Event.id)).all()]
