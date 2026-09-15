from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RoleName, User
from app.schemas.management import ManagerAssignmentRequest, ZoneAssignmentRequest
from app.security.context import SecurityContext, get_security_context
from app.security.delegation import (
    DelegationError,
    set_manager_zones,
    set_operator_manager,
    set_operator_zones,
)


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="You do not have access to this resource.")


def _current_admin(session: Session, context: SecurityContext) -> User:
    user = session.get(User, context.user_id)
    if user is None or user.role.name != RoleName.ADMIN:
        raise _forbidden()
    return user


def _target_user(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _user_data(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.name.value,
        "manager_id": user.manager_id,
        "zone_ids": sorted(scope.zone_id for scope in user.zone_scopes),
    }


@router.get("/users")
def list_users(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    admin = _current_admin(session, context)
    users = session.scalars(
        select(User).where(User.organization_id == admin.organization_id).order_by(User.username),
    ).all()
    return [_user_data(user) for user in users]


@router.put("/managers/{manager_id}/zones")
def update_manager_zones(
    manager_id: str,
    payload: ZoneAssignmentRequest,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    admin = _current_admin(session, context)
    manager = _target_user(session, manager_id)
    try:
        set_manager_zones(session, admin, manager, set(payload.zone_ids))
        session.commit()
    except DelegationError as error:
        session.rollback()
        raise _forbidden() from error
    return _user_data(manager)


@router.put("/operators/{operator_id}/manager")
def update_operator_manager(
    operator_id: str,
    payload: ManagerAssignmentRequest,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    admin = _current_admin(session, context)
    operator = _target_user(session, operator_id)
    manager = _target_user(session, payload.manager_id) if payload.manager_id is not None else None
    try:
        set_operator_manager(session, admin, operator, manager)
        session.commit()
    except DelegationError as error:
        session.rollback()
        raise _forbidden() from error
    return _user_data(operator)


@router.put("/operators/{operator_id}/zones")
def update_operator_zones(
    operator_id: str,
    payload: ZoneAssignmentRequest,
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    admin = _current_admin(session, context)
    operator = _target_user(session, operator_id)
    try:
        set_operator_zones(session, admin, operator, set(payload.zone_ids))
        session.commit()
    except DelegationError as error:
        session.rollback()
        raise _forbidden() from error
    return _user_data(operator)
