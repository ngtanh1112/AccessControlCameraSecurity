from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Camera
from app.security.context import SecurityContext, get_security_context
from app.security.gateway import AccessControlGateway, AccessDenied


router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])
gateway = AccessControlGateway()


def _forbidden(error: AccessDenied) -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


def _camera_data(camera: Camera) -> dict[str, str]:
    return {
        "id": camera.id,
        "name": camera.name,
        "zone_id": camera.zone_id,
        "status": camera.status.value,
    }


@router.get("")
def list_cameras(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, str]]:
    try:
        return gateway.execute(
            context,
            "camera:list",
            "camera",
            None,
            lambda decision: [
                _camera_data(camera)
                for camera in session.scalars(
                    select(Camera)
                    .where(Camera.id.in_(decision.allowed_camera_ids))
                    .order_by(Camera.id),
                ).all()
            ],
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error


@router.get("/{camera_id}")
def get_camera(
    camera_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        return gateway.execute(
            context,
            "camera:view_live",
            "camera",
            camera_id,
            lambda _decision: _camera_data(session.get(Camera, camera_id)),
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error
