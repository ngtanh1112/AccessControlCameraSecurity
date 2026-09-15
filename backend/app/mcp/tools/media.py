from __future__ import annotations

from app.db import SessionLocal
from app.mcp.base import MCPTool
from app.models import Event
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway
from app.services.integration_service import IntegrationService


def _event_data(event: Event) -> dict[str, object]:
    return {
        "id": event.id,
        "camera_id": event.camera_id,
        "recording_id": event.recording_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "description": event.description,
    }


class GetEventTool(MCPTool):
    name = "get_event"
    description = "Get one authorized event by ID."
    required_permission = "event:view"

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, object]:
        event_id = str(arguments["event_id"])
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "event:view",
                "event",
                event_id,
                lambda _decision: _event_data(IntegrationService(session).load_event(event_id)),
            )


class GetEventImageTool(MCPTool):
    name = "get_event_image"
    description = "Get image metadata for one authorized event."
    required_permission = "media:view_image"

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, object]:
        event_id = str(arguments["event_id"])
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "media:view_image",
                "media",
                event_id,
                lambda _decision: IntegrationService(session).load_image(event_id),
            )


class GetEventVideoTool(MCPTool):
    name = "get_event_video"
    description = "Get video metadata for one authorized event."
    required_permission = "media:view_video"

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, object]:
        event_id = str(arguments["event_id"])
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "media:view_video",
                "media",
                event_id,
                lambda _decision: IntegrationService(session).load_video(event_id),
            )


class GetLiveCameraTool(MCPTool):
    name = "get_live_camera"
    description = "Get live-view metadata for one authorized camera."
    required_permission = "camera:view_live"

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, object]:
        camera_id = str(arguments["camera_id"])
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "camera:view_live",
                "camera",
                camera_id,
                lambda _decision: IntegrationService(session).load_live(camera_id),
            )
