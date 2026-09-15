from __future__ import annotations

from fastapi import APIRouter

from app.mcp.registry import MCPToolRegistry, create_default_registry


router = APIRouter(prefix="/api/v1/registry", tags=["registry"])
registry: MCPToolRegistry = create_default_registry()


@router.get("/tools")
def list_tools() -> list[dict[str, str | None]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "required_permission": tool.required_permission,
        }
        for tool in registry.list()
    ]
