"""Organization and manager-scoped audit evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, RoleName, User
from app.security.context import SecurityContext, get_security_context


router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


@router.get("")
def list_audit_logs(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """Return only audit evidence the current role is entitled to inspect."""
    statement = select(AuditLog, User.username).join(User, User.id == AuditLog.user_id)

    if context.role == RoleName.ADMIN.value:
        statement = statement.where(User.organization_id == context.organization_id)
    elif context.role == RoleName.MANAGER.value:
        managed_operator_ids = select(User.id).where(
            User.manager_id == context.user_id,
            User.organization_id == context.organization_id,
        )
        statement = statement.where(
            User.organization_id == context.organization_id,
            or_(
                AuditLog.user_id == context.user_id,
                AuditLog.user_id.in_(managed_operator_ids),
            ),
        )
    else:
        raise _forbidden()

    return [
        {
            "id": audit.id,
            "timestamp": audit.created_at,
            "user": username,
            "action": audit.action,
            "resource_type": audit.resource_type,
            "resource_id": audit.resource_id,
            "decision": audit.decision,
            "reason": audit.reason,
            "stage": audit.stage,
            "request_id": audit.request_id,
        }
        for audit, username in session.execute(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()),
        ).all()
    ]
