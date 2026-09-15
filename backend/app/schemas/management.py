from __future__ import annotations

from pydantic import BaseModel


class ZoneAssignmentRequest(BaseModel):
    zone_ids: list[str]


class ManagerAssignmentRequest(BaseModel):
    manager_id: str | None
