from __future__ import annotations

from abc import ABC, abstractmethod

from app.security.context import SecurityContext


class MCPTool(ABC):
    name: str
    description: str
    required_permission: str | None

    @abstractmethod
    def execute(self, context: SecurityContext, arguments: dict):
        """Execute the tool with a validated security context."""
