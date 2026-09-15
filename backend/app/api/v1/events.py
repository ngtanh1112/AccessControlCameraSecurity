from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.security.context import SecurityContext, get_security_context
from app.security.gateway import AccessControlGateway, AccessDenied
from app.services.integration_service import IntegrationService
from app.services.search_service import (
    CameraScopeError,
    OffsetFilterValidationError,
    SearchService,
)


router = APIRouter(prefix="/api/v1/events", tags=["events"])
gateway = AccessControlGateway()


def _forbidden(error: AccessDenied) -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


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
    }


@router.get("")
def list_events(
    camera_id: str | None = None,
    recording_id: str | None = None,
    event_type: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    start_offset_ms: int | None = Query(default=None, ge=0),
    end_offset_ms: int | None = Query(default=None, ge=0),
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    resource_type = "camera" if camera_id is not None else "event"
    try:
        return gateway.execute(
            context,
            "event:search",
            resource_type,
            camera_id,
            lambda decision: [
                _event_data(event)
                for event in SearchService(session).search_events(
                    decision.allowed_camera_ids,
                    camera_id=camera_id,
                    recording_id=recording_id,
                    event_type=event_type,
                    from_time=from_time,
                    to_time=to_time,
                    start_offset_ms=start_offset_ms,
                    end_offset_ms=end_offset_ms,
                )
            ],
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error
    except CameraScopeError as error:
        raise HTTPException(status_code=403, detail="You do not have access to this resource.") from error
    except OffsetFilterValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{event_id}")
def get_event(
    event_id: str,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return gateway.execute(
            context,
            "event:view",
            "event",
            event_id,
            lambda _decision: _event_data(IntegrationService(session).load_event(event_id)),
            stage="DIRECT_API",
        )
    except AccessDenied as error:
        raise _forbidden(error) from error
