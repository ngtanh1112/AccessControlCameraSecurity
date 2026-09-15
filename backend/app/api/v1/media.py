from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.security.context import SecurityContext, get_security_context
from app.security.gateway import AccessControlGateway, AccessDenied
from app.services.integration_service import IntegrationService


router = APIRouter(prefix="/api/v1/media", tags=["media"])
gateway = AccessControlGateway()


def _forbidden(error: AccessDenied) -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


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
            lambda _decision: IntegrationService(session).load_image(event_id),
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
            lambda _decision: IntegrationService(session).load_video(event_id),
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
