from __future__ import annotations

from app.db import SessionLocal
from app.mcp.base import MCPTool
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway
from app.services.system_log_service import SystemLogService


class SearchSystemLogsTool(MCPTool):
    name = "search_system_logs"
    description = "Search system logs while filtering camera-scoped logs by authorization scope."
    required_permission = "system_log:view"

    def execute(self, context: SecurityContext, arguments: dict) -> list[dict[str, object]]:
        camera_id = arguments.get("camera_id")
        resource_type = "camera" if camera_id is not None else "system_log"
        with SessionLocal() as session:
            return AccessControlGateway().execute(
                context,
                "system_log:view",
                resource_type,
                str(camera_id) if camera_id is not None else None,
                lambda decision: SystemLogService(session).search(
                    allowed_camera_ids=decision.allowed_camera_ids,
                    camera_id=str(camera_id) if camera_id is not None else None,
                ),
            )
