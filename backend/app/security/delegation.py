"""Backend-enforced hierarchy and scope delegation rules."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import RoleName, User, UserZoneScope, Zone


class DelegationError(PermissionError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _zone_ids_for_user(session: Session, user_id: str) -> set[str]:
    return set(
        session.scalars(
            select(UserZoneScope.zone_id).where(UserZoneScope.user_id == user_id),
        ).all(),
    )


def _validate_zone_ids(session: Session, organization_id: str, zone_ids: set[str]) -> None:
    zones = session.scalars(select(Zone).where(Zone.id.in_(zone_ids))).all() if zone_ids else []
    if len(zones) != len(zone_ids):
        raise DelegationError("zone_not_found")
    if any(zone.organization_id != organization_id for zone in zones):
        raise DelegationError("organization_mismatch")


def _replace_user_zone_scopes(
    session: Session,
    user: User,
    zone_ids: set[str],
    assigned_by_user_id: str,
) -> None:
    session.execute(delete(UserZoneScope).where(UserZoneScope.user_id == user.id))
    for zone_id in sorted(zone_ids):
        session.add(
            UserZoneScope(
                user_id=user.id,
                zone_id=zone_id,
                assigned_by_user_id=assigned_by_user_id,
            ),
        )


def set_manager_zones(
    session: Session,
    admin: User,
    manager: User,
    zone_ids: set[str],
) -> None:
    if admin.role.name != RoleName.ADMIN:
        raise DelegationError("admin_role_required")
    if manager.role.name != RoleName.MANAGER:
        raise DelegationError("target_not_manager")
    if manager.organization_id != admin.organization_id:
        raise DelegationError("organization_mismatch")
    _validate_zone_ids(session, manager.organization_id, zone_ids)

    managed_operators = session.scalars(
        select(User).where(User.manager_id == manager.id),
    ).all()
    for operator in managed_operators:
        if operator.role.name != RoleName.OPERATOR:
            continue
        if not _zone_ids_for_user(session, operator.id).issubset(zone_ids):
            raise DelegationError("delegated_scope_exceeds_manager_scope")

    _replace_user_zone_scopes(session, manager, zone_ids, admin.id)


def set_operator_manager(
    session: Session,
    admin: User,
    operator: User,
    manager: User | None,
) -> None:
    if admin.role.name != RoleName.ADMIN:
        raise DelegationError("admin_role_required")
    if operator.role.name != RoleName.OPERATOR:
        raise DelegationError("target_not_operator")
    if operator.organization_id != admin.organization_id:
        raise DelegationError("organization_mismatch")
    if manager is None:
        operator.manager_id = None
        return
    if manager.role.name != RoleName.MANAGER:
        raise DelegationError("target_not_manager")
    if manager.organization_id != operator.organization_id:
        raise DelegationError("organization_mismatch")

    operator_zone_ids = _zone_ids_for_user(session, operator.id)
    manager_zone_ids = _zone_ids_for_user(session, manager.id)
    if not operator_zone_ids.issubset(manager_zone_ids):
        raise DelegationError("delegated_scope_exceeds_manager_scope")
    operator.manager_id = manager.id


def set_operator_zones(
    session: Session,
    actor: User,
    operator: User,
    zone_ids: set[str],
) -> None:
    if operator.role.name != RoleName.OPERATOR:
        raise DelegationError("target_not_operator")
    if operator.organization_id != actor.organization_id:
        raise DelegationError("organization_mismatch")
    _validate_zone_ids(session, operator.organization_id, zone_ids)

    if operator.manager_id is not None:
        manager_zone_ids = _zone_ids_for_user(session, operator.manager_id)
        if not zone_ids.issubset(manager_zone_ids):
            raise DelegationError("delegated_scope_exceeds_manager_scope")
    _replace_user_zone_scopes(session, operator, zone_ids, actor.id)


def manager_set_operator_zones(
    session: Session,
    manager: User,
    operator: User,
    zone_ids: set[str],
) -> None:
    if manager.role.name != RoleName.MANAGER:
        raise DelegationError("manager_role_required")
    if operator.role.name != RoleName.OPERATOR or operator.manager_id != manager.id:
        raise DelegationError("target_not_managed_operator")
    if operator.organization_id != manager.organization_id:
        raise DelegationError("organization_mismatch")

    manager_zone_ids = _zone_ids_for_user(session, manager.id)
    if not zone_ids.issubset(manager_zone_ids):
        raise DelegationError("delegated_scope_exceeds_manager_scope")
    set_operator_zones(session, manager, operator, zone_ids)
