from __future__ import annotations

from app.mcp.base import MCPTool
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway
from app.services.notification_service import NotificationService


class CreateAlertTool(MCPTool):
    name = "create_alert"
    description = "Create an in-memory alert notification for an authorized camera."
    required_permission = "alert:create"

    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    def execute(self, context: SecurityContext, arguments: dict) -> dict[str, str]:
        camera_id = str(arguments["camera_id"])
        message = str(arguments.get("message", "Camera alert"))

        def create_alert(_decision) -> dict[str, str]:
            return self.notification_service.create_alert(
                camera_id=camera_id,
                message=message,
                created_by=context.user_id,
            )

        return AccessControlGateway().execute(
            context,
            "alert:create",
            "camera",
            camera_id,
            create_alert,
        )
