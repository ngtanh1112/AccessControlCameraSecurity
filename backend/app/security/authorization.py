"""Resource-scope authorization rules for the access-control boundary."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Camera, Event, RoleName, Zone
from app.security.context import SecurityContext


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    action: str
    resource_type: str
    resource_id: str | None
    allowed_zone_ids: list[str]
    allowed_camera_ids: list[str]


def _decision(
    *,
    allowed: bool,
    reason: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    allowed_zone_ids: list[str] | None = None,
    allowed_camera_ids: list[str] | None = None,
) -> AuthorizationDecision:
    return AuthorizationDecision(
        allowed=allowed,
        reason=reason,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        allowed_zone_ids=allowed_zone_ids or [],
        allowed_camera_ids=allowed_camera_ids or [],
    )


def _allowed_zone_ids(session: Session, context: SecurityContext) -> list[str]:
    if context.role == RoleName.ADMIN.value:
        statement = select(Zone.id).where(Zone.organization_id == context.organization_id)
    else:
        statement = select(Zone.id).where(
            Zone.organization_id == context.organization_id,
            Zone.id.in_(context.allowed_zone_ids),
        )
    return sorted(session.scalars(statement).all())


def _allowed_camera_ids(
    session: Session,
    context: SecurityContext,
    allowed_zone_ids: list[str],
) -> list[str]:
    if not allowed_zone_ids:
        return []
    statement = select(Camera.id).where(
        Camera.organization_id == context.organization_id,
        Camera.zone_id.in_(allowed_zone_ids),
    )
    return sorted(session.scalars(statement).all())


def _resolve_resource(
    session: Session,
    resource_type: str,
    resource_id: str,
) -> Camera | None:
    if resource_type == "camera":
        return session.get(Camera, resource_id)

    if resource_type in {"event", "media"}:
        event = session.get(Event, resource_id)
        return event.camera if event is not None else None

    return None


def authorize(
    context: SecurityContext,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
) -> AuthorizationDecision:
    """Authorize a resource access or return the search scope for an action.

    This function deliberately returns a decision instead of raising so every caller
    can use the same result at the access-control boundary.
    """
    if action not in context.permissions:
        return _decision(
            allowed=False,
            reason="permission_missing",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    with SessionLocal() as session:
        allowed_zone_ids = _allowed_zone_ids(session, context)
        allowed_camera_ids = _allowed_camera_ids(session, context, allowed_zone_ids)

        if resource_id is None:
            return _decision(
                allowed=True,
                reason="allowed",
                action=action,
                resource_type=resource_type,
                resource_id=None,
                allowed_zone_ids=allowed_zone_ids,
                allowed_camera_ids=allowed_camera_ids,
            )

        camera = _resolve_resource(session, resource_type, resource_id)
        if camera is None:
            return _decision(
                allowed=False,
                reason="resource_not_found",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed_zone_ids=allowed_zone_ids,
                allowed_camera_ids=allowed_camera_ids,
            )

        if camera.organization_id != context.organization_id:
            return _decision(
                allowed=False,
                reason="organization_mismatch",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed_zone_ids=allowed_zone_ids,
                allowed_camera_ids=allowed_camera_ids,
            )

        if camera.zone_id not in allowed_zone_ids:
            return _decision(
                allowed=False,
                reason="resource_out_of_scope",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed_zone_ids=allowed_zone_ids,
                allowed_camera_ids=allowed_camera_ids,
            )

        return _decision(
            allowed=True,
            reason="allowed",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            allowed_zone_ids=allowed_zone_ids,
            allowed_camera_ids=allowed_camera_ids,
        )
