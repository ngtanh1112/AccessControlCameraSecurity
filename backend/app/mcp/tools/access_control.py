from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal
from app.mcp.base import MCPTool
from app.models import Camera, Zone
from app.security.authorization import authorize
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway


class GetMyPermissionsTool(MCPTool):
    name = "get_my_permissions"
    description = "Return the permissions attached to the current user context."
    required_permission = None

    def execute(self, context: SecurityContext, arguments: dict) -> list[str]:
        return sorted(context.permissions)


class GetMyZonesTool(MCPTool):
    name = "get_my_zones"
    description = "Return zones available to the current user."
    required_permission = "camera:list"

    def execute(self, context: SecurityContext, arguments: dict) -> list[dict[str, str]]:
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "camera:list",
                "camera",
                None,
                lambda decision: [
                    {"id": zone.id, "name": zone.name}
                    for zone in session.scalars(
                        select(Zone)
                        .where(Zone.id.in_(decision.allowed_zone_ids))
                        .order_by(Zone.id),
                    ).all()
                ],
            )


class GetMyCamerasTool(MCPTool):
    name = "get_my_cameras"
    description = "Return cameras available to the current user."
    required_permission = "camera:list"

    def execute(self, context: SecurityContext, arguments: dict) -> list[dict[str, str]]:
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "camera:list",
                "camera",
                None,
                lambda decision: [
                    {
                        "id": camera.id,
                        "name": camera.name,
                        "zone_id": camera.zone_id,
                    }
                    for camera in session.scalars(
                        select(Camera)
                        .where(Camera.id.in_(decision.allowed_camera_ids))
                        .order_by(Camera.id),
                    ).all()
                ],
            )


class CanAccessTool(MCPTool):
    name = "can_access"
    description = "Return an authorization decision for a requested resource."
    required_permission = None

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, object]:
        action = str(arguments["action"])
        resource_type = str(arguments["resource_type"])
        resource_id = arguments.get("resource_id")
        decision = authorize(
            context,
            action,
            resource_type,
            str(resource_id) if resource_id is not None else None,
        )
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "allowed_camera_ids": decision.allowed_camera_ids,
        }
