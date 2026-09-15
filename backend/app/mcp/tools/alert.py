from __future__ import annotations

from uuid import uuid4

from app.mcp.base import MCPTool
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway


_alerts: list[dict[str, str]] = []


class CreateAlertTool(MCPTool):
    name = "create_alert"
    description = "Create a simple in-memory alert for an authorized camera."
    required_permission = "alert:create"

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, str]:
        camera_id = str(arguments["camera_id"])
        message = str(arguments.get("message", "Camera alert"))

        def create_alert(_decision) -> dict[str, str]:
            alert = {
                "id": str(uuid4()),
                "camera_id": camera_id,
                "message": message,
                "created_by": context.user_id,
            }
            _alerts.append(alert)
            return alert

        return AccessControlGateway().execute(
            context,
            "alert:create",
            "camera",
            camera_id,
            create_alert,
        )
