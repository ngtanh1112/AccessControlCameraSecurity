from __future__ import annotations

from app.agents.subagents.search_agent import SubAgentResult
from app.mcp.registry import MCPToolRegistry
from app.security.context import SecurityContext


class SystemSubAgent:
    name = "SystemSubAgent"

    def __init__(self, registry: MCPToolRegistry) -> None:
        self.registry = registry

    def execute(self, context: SecurityContext, entities: dict[str, object]) -> SubAgentResult:
        tool = self.registry.get("search_system_logs")
        if tool is None:
            raise LookupError("MCP tool is not registered: search_system_logs")
        return SubAgentResult(
            self.name,
            "search_system_logs",
            tool.execute(context, {"camera_id": entities.get("camera_id")}),
        )
