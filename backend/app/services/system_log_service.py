"""Scoped retrieval of persisted system logs."""

from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import SystemLog


class SystemLogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        *,
        allowed_camera_ids: Collection[str],
        camera_id: str | None = None,
    ) -> list[dict[str, object]]:
        """Return global logs plus only camera logs that are within the Gateway scope."""
        statement = select(SystemLog)
        if camera_id is not None:
            statement = statement.where(SystemLog.camera_id == camera_id)
        elif allowed_camera_ids:
            statement = statement.where(
                or_(
                    SystemLog.camera_id.is_(None),
                    SystemLog.camera_id.in_(sorted(allowed_camera_ids)),
                ),
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
            for log in self.session.scalars(statement.order_by(SystemLog.created_at, SystemLog.id)).all()
        ]
