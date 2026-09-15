"""Persist pre-agent execution trace state for each conversation request."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ExecutionTrace
from app.security.context import SecurityContext


def create_execution_trace(
    context: SecurityContext,
    *,
    intent: str | None,
    resource_type: str | None,
    resource_id: str | None,
) -> str:
    trace_id = str(uuid4())
    with SessionLocal.begin() as session:
        session.add(
            ExecutionTrace(
                id=trace_id,
                request_id=context.request_id,
                user_id=context.user_id,
                intent=intent,
                resource_type=resource_type,
                resource_id=resource_id,
                pre_auth_decision=None,
                agent_invoked=False,
                mcp_invoked=False,
                backend_invoked=False,
            ),
        )
    return trace_id


def record_pre_auth_decision(trace_id: str, decision: str) -> None:
    with SessionLocal.begin() as session:
        trace = session.get(ExecutionTrace, trace_id)
        if trace is not None:
            trace.pre_auth_decision = decision


def record_runtime_invocations(
    request_id: str,
    *,
    agent_invoked: bool,
    mcp_invoked: bool,
    backend_invoked: bool,
) -> None:
    with SessionLocal.begin() as session:
        trace = session.scalar(
            select(ExecutionTrace)
            .where(ExecutionTrace.request_id == request_id)
            .order_by(ExecutionTrace.created_at.desc()),
        )
        if trace is not None:
            trace.agent_invoked = agent_invoked
            trace.mcp_invoked = mcp_invoked
            trace.backend_invoked = backend_invoked
