"""Deterministic, traceable conversation orchestration endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.entity_extractor import EntityExtractor
from app.agents.intent_router import IntentRouter
from app.agents.master import MasterAgent
from app.api.v1.registry import registry
from app.security.capability_resolver import resolve_capability
from app.security.context import SecurityContext, get_security_context
from app.security.execution_trace import record_runtime_invocations
from app.security.gateway import AccessDenied
from app.security.pre_authorization import PreAuthorizationGate
from app.services.search_service import OffsetFilterValidationError


router = APIRouter(prefix="/api/v1/conversations", tags=["conversation"])


class ConversationMessage(BaseModel):
    message: str = Field(min_length=1)


def _deny_response(
    context: SecurityContext,
    intent: str,
) -> dict[str, object]:
    return {
        "request_id": context.request_id,
        "intent": intent,
        "pre_authorization": "DENY",
        "agent_invoked": False,
        "agent": None,
        "mcp_invoked": False,
        "tool": None,
        "backend_invoked": False,
        "decision": "DENY",
        "answer": "Bạn không có quyền truy cập tài nguyên này.",
        "data": None,
    }


def _event_answer_data(data: object) -> object:
    """Expose video-ready event fields without tying the agent to persistence models."""
    if not isinstance(data, list):
        return data
    formatted: list[object] = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item:
            formatted.append(item)
            continue
        formatted.append(
            {
                "event_id": item["id"],
                "camera_id": item.get("camera_id"),
                "recording_id": item.get("recording_id"),
                "event_type": item.get("event_type"),
                "occurred_at": item.get("occurred_at"),
                "start_offset_ms": item.get("start_offset_ms"),
                "end_offset_ms": item.get("end_offset_ms"),
                "confidence": item.get("confidence"),
                "snapshot_url": item.get("snapshot_url"),
                "clip_url": item.get("clip_url"),
            },
        )
    return formatted


def _answer(intent: str, data: object) -> str:
    count = len(data) if isinstance(data, list) else None
    if intent == "SEARCH_EVENT":
        return f"Tìm thấy {count or 0} sự kiện trong khoảng được yêu cầu."
    if intent == "LIST_MY_CAMERAS":
        return f"Tìm thấy {count or 0} camera bạn có thể xem."
    return "Yêu cầu đã được xử lý."


@router.post("/messages")
def send_message(
    payload: ConversationMessage,
    context: Annotated[SecurityContext, Depends(get_security_context)],
) -> dict[str, object]:
    """Run pre-auth before dispatching a deterministic agent to MCP tools."""
    intent = IntentRouter().route(payload.message)
    entities = EntityExtractor().extract(payload.message)
    pre_authorization = PreAuthorizationGate().evaluate(context, intent, entities)

    if not pre_authorization.allowed:
        return _deny_response(context, intent.value)

    # Capability resolution is a routing guard; it does not decide resource access.
    if resolve_capability(context, intent) is None:
        return _deny_response(context, intent.value)

    master_agent = MasterAgent(registry)
    try:
        result = master_agent.execute(context, intent, entities)
    except AccessDenied:
        # Gateway remains authoritative if scope changes after pre-authorization.
        record_runtime_invocations(
            context.request_id,
            agent_invoked=True,
            mcp_invoked=True,
            backend_invoked=False,
        )
        return _deny_response(context, intent.value)
    except OffsetFilterValidationError as error:
        # The search reached MCP/Gateway/SearchService.  Direct APIs retain their
        # strict 422 validation; the chat response keeps its execution metadata.
        record_runtime_invocations(
            context.request_id,
            agent_invoked=True,
            mcp_invoked=True,
            backend_invoked=True,
        )
        return {
            "request_id": context.request_id,
            "intent": intent.value,
            "pre_authorization": "ALLOW",
            "agent_invoked": True,
            "agent": "SearchCameraSubAgent",
            "mcp_invoked": True,
            "tool": "search_events",
            "backend_invoked": True,
            "decision": "ALLOW",
            "answer": str(error),
            "data": [],
        }

    record_runtime_invocations(
        context.request_id,
        agent_invoked=True,
        mcp_invoked=True,
        backend_invoked=True,
    )
    data = _event_answer_data(result.data) if intent.value == "SEARCH_EVENT" else result.data
    return {
        "request_id": context.request_id,
        "intent": intent.value,
        "pre_authorization": "ALLOW",
        **master_agent.format_response_metadata(result),
        "decision": "ALLOW",
        "answer": _answer(intent.value, data),
        "data": data,
    }
