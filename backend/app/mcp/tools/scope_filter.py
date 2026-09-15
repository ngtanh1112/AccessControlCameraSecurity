from __future__ import annotations

from app.mcp.base import MCPTool
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway


class FilterCameraIdsTool(MCPTool):
    name = "filter_camera_ids"
    description = "Filter camera IDs against the current server-side authorization scope."
    required_permission = "camera:list"

    def execute(self, context: SecurityContext, arguments: dict) -> list[str]:
        requested = arguments.get("camera_ids")
        gateway = AccessControlGateway()
        if requested is None:
            return gateway.execute(
                context,
                "camera:list",
                "camera",
                None,
                lambda decision: decision.allowed_camera_ids,
            )

        requested_ids = [str(camera_id) for camera_id in requested]
        for camera_id in requested_ids:
            gateway.execute(
                context,
                "camera:list",
                "camera",
                camera_id,
                lambda _decision: None,
            )
        return requested_ids
