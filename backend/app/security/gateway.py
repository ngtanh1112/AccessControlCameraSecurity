"""Reusable final access-control gateway for protected operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.security.audit import write_audit
from app.security.authorization import AuthorizationDecision, authorize
from app.security.context import SecurityContext


Result = TypeVar("Result")


class AccessDenied(PermissionError):
    def __init__(self, decision: AuthorizationDecision) -> None:
        super().__init__("Access denied")
        self.decision = decision


class AccessControlGateway:
    def execute(
        self,
        context: SecurityContext,
        action: str,
        resource_type: str,
        resource_id: str | None,
        operation: Callable[[AuthorizationDecision], Result],
        *,
        stage: str = "TOOL_ENFORCEMENT",
    ) -> Result:
        decision = authorize(context, action, resource_type, resource_id)
        write_audit(context, decision, stage=stage)
        if not decision.allowed:
            raise AccessDenied(decision)
        return operation(decision)
