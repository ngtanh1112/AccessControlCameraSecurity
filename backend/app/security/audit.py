"""Audit persistence for access-control decisions."""

from __future__ import annotations

from uuid import uuid4

from app.db import SessionLocal
from app.models import AuditLog
from app.security.authorization import AuthorizationDecision
from app.security.context import SecurityContext


def write_audit(
    context: SecurityContext,
    decision: AuthorizationDecision,
    *,
    stage: str,
) -> None:
    if stage not in {"TOOL_ENFORCEMENT", "DIRECT_API", "PRE_AUTHORIZATION"}:
        raise ValueError(
            "Audit stage must be TOOL_ENFORCEMENT, DIRECT_API, or PRE_AUTHORIZATION",
        )

    with SessionLocal.begin() as session:
        session.add(
            AuditLog(
                id=str(uuid4()),
                request_id=context.request_id,
                user_id=context.user_id,
                action=decision.action,
                resource_type=decision.resource_type,
                resource_id=decision.resource_id,
                decision="ALLOW" if decision.allowed else "DENY",
                reason=decision.reason,
                stage=stage,
            ),
        )
