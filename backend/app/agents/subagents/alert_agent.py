from __future__ import annotations

from app.agents.subagents.search_agent import SubAgentResult
from app.mcp.registry import MCPToolRegistry
from app.security.context import SecurityContext


class AlertSubAgent:
    name = "AlertSubAgent"

    def __init__(self, registry: MCPToolRegistry) -> None:
        self.registry = registry

    def execute(self, context: SecurityContext, entities: dict[str, object]) -> SubAgentResult:
        tool = self.registry.get("create_alert")
        if tool is None:
            raise LookupError("MCP tool is not registered: create_alert")
        return SubAgentResult(
            self.name,
            "create_alert",
            tool.execute(
                context,
                {
                    "camera_id": entities.get("camera_id"),
                    "message": entities.get("message", "Camera alert"),
                },
            ),
        )
