from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RoleName, User
from app.schemas.management import ZoneAssignmentRequest
from app.security.context import SecurityContext, get_security_context
from app.security.delegation import DelegationError, manager_set_operator_zones


router = APIRouter(prefix="/api/v1/management", tags=["management"])


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


def _current_manager(session: Session, context: SecurityContext) -> User:
    user = session.get(User, context.user_id)
    if user is None or user.role.name != RoleName.MANAGER:
        raise _forbidden()
    return user


def _operator_data(operator: User) -> dict[str, object]:
    return {
        "id": operator.id,
        "username": operator.username,
        "display_name": operator.display_name,
        "role": operator.role.name.value,
        "manager_id": operator.manager_id,
        "zone_ids": sorted(scope.zone_id for scope in operator.zone_scopes),
    }


@router.get("/operators")
def list_managed_operators(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    manager = _current_manager(session, context)
    operators = session.scalars(
        select(User)
        .join(User.role)
        .where(User.manager_id == manager.id, User.role.has(name=RoleName.OPERATOR))
        .order_by(User.username),
    ).all()
    return [_operator_data(operator) for operator in operators]


@router.put("/operators/{operator_id}/zones")
def update_managed_operator_zones(
    operator_id: str,
    payload: ZoneAssignmentRequest,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    manager = _current_manager(session, context)
    operator = session.get(User, operator_id)
    if operator is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        manager_set_operator_zones(session, manager, operator, set(payload.zone_ids))
        session.commit()
    except DelegationError as error:
        session.rollback()
        raise _forbidden() from error
    return _operator_data(operator)
