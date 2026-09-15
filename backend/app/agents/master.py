"""Deterministic sub-agent dispatch only; access decisions remain outside this layer."""

from __future__ import annotations

from typing import Mapping

from app.agents.intent_router import Intent
from app.agents.subagents.alert_agent import AlertSubAgent
from app.agents.subagents.search_agent import SearchCameraSubAgent, SubAgentResult
from app.agents.subagents.system_agent import SystemSubAgent
from app.mcp.registry import MCPToolRegistry
from app.security.context import SecurityContext


class MasterAgent:
    def __init__(self, registry: MCPToolRegistry) -> None:
        self.search_agent = SearchCameraSubAgent(registry)
        self.alert_agent = AlertSubAgent(registry)
        self.system_agent = SystemSubAgent(registry)

    def execute(
        self,
        context: SecurityContext,
        intent: Intent,
        entities: Mapping[str, object],
    ) -> SubAgentResult:
        if intent in {
            Intent.LIST_MY_CAMERAS,
            Intent.SEARCH_EVENT,
            Intent.VIEW_EVENT,
            Intent.VIEW_IMAGE,
            Intent.VIEW_VIDEO,
            Intent.VIEW_LIVE_CAMERA,
        }:
            return self.search_agent.execute(context, intent, entities)
        if intent == Intent.CREATE_ALERT:
            return self.alert_agent.execute(context, dict(entities))
        if intent == Intent.SEARCH_SYSTEM_LOG:
            return self.system_agent.execute(context, dict(entities))
        raise ValueError(f"Unsupported MasterAgent intent: {intent.value}")

    @staticmethod
    def format_response_metadata(result: SubAgentResult) -> dict[str, object]:
        """Return execution metadata after a successful deterministic dispatch."""
        return {
            "agent_invoked": True,
            "agent": result.agent,
            "mcp_invoked": True,
            "tool": result.tool,
            "backend_invoked": True,
        }
