from __future__ import annotations

from app.mcp.base import MCPTool


class MCPToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list(self) -> list[MCPTool]:
        return [self._tools[name] for name in sorted(self._tools)]


def create_default_registry() -> MCPToolRegistry:
    from app.mcp.tools.access_control import (
        CanAccessTool,
        GetMyCamerasTool,
        GetMyPermissionsTool,
        GetMyZonesTool,
    )
    from app.mcp.tools.alert import CreateAlertTool
    from app.mcp.tools.media import (
        GetEventImageTool,
        GetEventTool,
        GetEventVideoTool,
        GetLiveCameraTool,
    )
    from app.mcp.tools.scope_filter import FilterCameraIdsTool
    from app.mcp.tools.search import SearchEventsTool
    from app.mcp.tools.system_log import SearchSystemLogsTool

    registry = MCPToolRegistry()
    for tool in (
        GetMyPermissionsTool(),
        GetMyZonesTool(),
        GetMyCamerasTool(),
        CanAccessTool(),
        FilterCameraIdsTool(),
        SearchEventsTool(),
        GetEventTool(),
        GetEventImageTool(),
        GetEventVideoTool(),
        GetLiveCameraTool(),
        CreateAlertTool(),
        SearchSystemLogsTool(),
    ):
        registry.register(tool)
    return registry
