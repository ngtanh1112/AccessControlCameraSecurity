"""Early authorization optimization before any future Agent/MCP invocation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.agents.intent_router import Intent
from app.security.audit import write_audit
from app.security.authorization import AuthorizationDecision, authorize
from app.security.capability_resolver import action_for_intent
from app.security.context import SecurityContext
from app.security.execution_trace import create_execution_trace, record_pre_auth_decision


@dataclass(frozen=True)
class PreAuthorizationResult:
    allowed: bool
    reason: str
    action: str | None
    resource_type: str | None
    resource_id: str | None
    allowed_camera_ids: list[str]


def _resource_for_request(
    intent: Intent,
    entities: Mapping[str, object],
) -> tuple[str | None, str | None]:
    event_id = entities.get("event_id")
    camera_id = entities.get("camera_id")
    if intent in {Intent.VIEW_EVENT}:
        return "event", str(event_id) if event_id is not None else None
    if intent in {Intent.VIEW_IMAGE, Intent.VIEW_VIDEO}:
        return "media", str(event_id) if event_id is not None else None
    if intent == Intent.VIEW_LIVE_CAMERA:
        return "camera", str(camera_id) if camera_id is not None else None
    if intent == Intent.SEARCH_EVENT and camera_id is not None:
        return "camera", str(camera_id)
    if intent == Intent.SEARCH_EVENT:
        return "event", None
    if intent == Intent.LIST_MY_CAMERAS:
        return "camera", None
    return None, None


class PreAuthorizationGate:
    """Runs deterministic early checks; Gateway remains the final enforcement layer."""

    def evaluate(
        self,
        context: SecurityContext,
        intent: Intent,
        entities: Mapping[str, object],
    ) -> PreAuthorizationResult:
        action = action_for_intent(intent)
        resource_type, resource_id = _resource_for_request(intent, entities)
        trace_id = create_execution_trace(
            context,
            intent=intent.value,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if action is None:
            result = PreAuthorizationResult(
                allowed=False,
                reason="unknown_intent",
                action=None,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed_camera_ids=[],
            )
            self._record_early_deny(context, trace_id, result)
            return result

        decision = authorize(context, action, resource_type or "request", resource_id)
        result = PreAuthorizationResult(
            allowed=decision.allowed,
            reason=decision.reason,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            allowed_camera_ids=decision.allowed_camera_ids,
        )
        record_pre_auth_decision(trace_id, "ALLOW" if result.allowed else "DENY")
        if not result.allowed:
            self._write_early_deny_audit(context, decision)
        return result

    def _record_early_deny(
        self,
        context: SecurityContext,
        trace_id: str,
        result: PreAuthorizationResult,
    ) -> None:
        record_pre_auth_decision(trace_id, "DENY")
        write_audit(
            context,
            AuthorizationDecision(
                allowed=False,
                reason=result.reason,
                action=result.action or "unknown",
                resource_type=result.resource_type or "request",
                resource_id=result.resource_id,
                allowed_zone_ids=[],
                allowed_camera_ids=[],
            ),
            stage="PRE_AUTHORIZATION",
        )

    def _write_early_deny_audit(
        self,
        context: SecurityContext,
        decision: AuthorizationDecision,
    ) -> None:
        write_audit(context, decision, stage="PRE_AUTHORIZATION")
