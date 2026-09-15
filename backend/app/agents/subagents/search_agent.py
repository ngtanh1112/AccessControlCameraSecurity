from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.agents.intent_router import Intent
from app.mcp.registry import MCPToolRegistry
from app.security.context import SecurityContext


@dataclass(frozen=True)
class SubAgentResult:
    agent: str
    tool: str
    data: object


class SearchCameraSubAgent:
    name = "SearchCameraSubAgent"

    def __init__(self, registry: MCPToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        context: SecurityContext,
        intent: Intent,
        entities: Mapping[str, object],
    ) -> SubAgentResult:
        tool_name, arguments = self._tool_request(intent, entities)
        tool = self.registry.get(tool_name)
        if tool is None:
            raise LookupError(f"MCP tool is not registered: {tool_name}")
        return SubAgentResult(self.name, tool_name, tool.execute(context, arguments))

    @staticmethod
    def _tool_request(intent: Intent, entities: Mapping[str, object]) -> tuple[str, dict]:
        if intent == Intent.LIST_MY_CAMERAS:
            return "get_my_cameras", {}
        if intent == Intent.SEARCH_EVENT:
            return "search_events", {
                "camera_id": entities.get("camera_id"),
                "recording_id": entities.get("recording_id"),
                "event_type": entities.get("event_type"),
                "from_time": entities.get("from_time"),
                "to_time": entities.get("to_time"),
                "start_offset_ms": entities.get("start_offset_ms"),
                "end_offset_ms": entities.get("end_offset_ms"),
            }
        if intent == Intent.VIEW_EVENT:
            return "get_event", {"event_id": entities.get("event_id")}
        if intent == Intent.VIEW_IMAGE:
            return "get_event_image", {"event_id": entities.get("event_id")}
        if intent == Intent.VIEW_VIDEO:
            return "get_event_video", {"event_id": entities.get("event_id")}
        if intent == Intent.VIEW_LIVE_CAMERA:
            return "get_live_camera", {"camera_id": entities.get("camera_id")}
        raise ValueError(f"Unsupported SearchCameraSubAgent intent: {intent.value}")
