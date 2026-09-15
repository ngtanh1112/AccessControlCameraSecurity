from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.security.context import SecurityContext, get_security_context
from app.security.gateway import AccessControlGateway, AccessDenied
from app.services.integration_service import IntegrationService
from app.services.media_storage import MediaStorage


router = APIRouter(prefix="/api/v1/media", tags=["media"])
gateway = AccessControlGateway()
storage = MediaStorage()


def _forbidden(error: AccessDenied) -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


def _media_response(session: Session, event_id: str, kind: str):
    integration = IntegrationService(session)
    event = integration.load_event(event_id)
    stored_path = event.snapshot_path if event is not None and kind == "image" else event.clip_path if event is not None else None
    path = storage.resolve(stored_path)
    if path is not None and path.is_file():
        return FileResponse(path, media_type="image/jpeg" if kind == "image" else "video/mp4")
    return integration.load_image(event_id) if kind == "image" else integration.load_video(event_id)


@router.get("/events/{event_id}/image")
def get_event_image(
    event_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return gateway.execute(
            context,
            "media:view_image",
            "media",
            event_id,
            lambda _decision: _media_response(session, event_id, "image"),
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error


@router.get("/events/{event_id}/video")
def get_event_video(
    event_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return gateway.execute(
            context,
            "media:view_video",
            "media",
            event_id,
            lambda _decision: _media_response(session, event_id, "video"),
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error


@router.get("/cameras/{camera_id}/live")
def get_camera_live(
    camera_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return gateway.execute(
            context,
            "camera:view_live",
            "camera",
            camera_id,
            lambda _decision: IntegrationService(session).load_live(camera_id),
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error
