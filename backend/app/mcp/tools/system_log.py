from __future__ import annotations

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.mcp.base import MCPTool
from app.models import SystemLog
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway


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
                lambda decision: self._search(
                    session,
                    decision.allowed_camera_ids,
                    str(camera_id) if camera_id is not None else None,
                ),
            )

    @staticmethod
    def _search(session, allowed_camera_ids: list[str], camera_id: str | None) -> list[dict[str, object]]:
        statement = select(SystemLog)
        if camera_id is not None:
            statement = statement.where(SystemLog.camera_id == camera_id)
        elif allowed_camera_ids:
            statement = statement.where(
                or_(SystemLog.camera_id.is_(None), SystemLog.camera_id.in_(allowed_camera_ids)),
            )
        else:
            statement = statement.where(SystemLog.camera_id.is_(None))
        return [
            {
                "id": log.id,
                "source": log.source,
                "level": log.level,
                "message": log.message,
                "camera_id": log.camera_id,
                "created_at": log.created_at,
            }
            for log in session.scalars(statement.order_by(SystemLog.created_at, SystemLog.id)).all()
        ]
