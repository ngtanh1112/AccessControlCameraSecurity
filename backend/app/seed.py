"""Create deterministic demo metadata for the local SQLite database."""

from __future__ import annotations

from datetime import datetime
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db import SessionLocal, create_all
from app.models import (
    Camera,
    CameraStatus,
    Event,
    Organization,
    Permission,
    Role,
    RoleName,
    RolePermission,
    User,
    UserZoneScope,
    Zone,
)


DEMO_ORGANIZATION_ID = "ORG-DEMO"
ZONE_A_ID = "ZONE-A"
ZONE_B_ID = "ZONE-B"

ROLE_IDS = {
    RoleName.ADMIN: "ROLE-ADMIN",
    RoleName.MANAGER: "ROLE-MANAGER",
    RoleName.OPERATOR: "ROLE-OPERATOR",
}
USER_IDS = {
    "admin": "USER-ADMIN",
    "manager": "USER-MANAGER",
    "alice": "USER-ALICE",
    "bob": "USER-BOB",
}

PERMISSION_CODES = (
    "camera:list",
    "camera:view_live",
    "event:search",
    "event:view",
    "media:view_image",
    "media:view_video",
    "alert:create",
    "system_log:view",
    "audit:view",
    "operator:manage",
    "scope:assign",
    "system:admin",
)

MANAGER_PERMISSION_CODES = (
    "camera:list",
    "camera:view_live",
    "event:search",
    "event:view",
    "media:view_image",
    "media:view_video",
    "alert:create",
    "system_log:view",
    "operator:manage",
    "scope:assign",
    "audit:view",
)

OPERATOR_PERMISSION_CODES = (
    "camera:list",
    "camera:view_live",
    "event:search",
    "event:view",
    "media:view_image",
    "media:view_video",
    "alert:create",
)

ROLE_PERMISSION_CODES = {
    RoleName.ADMIN: PERMISSION_CODES,
    RoleName.MANAGER: MANAGER_PERMISSION_CODES,
    RoleName.OPERATOR: OPERATOR_PERMISSION_CODES,
}

# Fixed PBKDF2 hashes keep demo seed data deterministic. Authentication is added later.
PASSWORD_HASHES = {
    "admin": "$pbkdf2-sha256$29000$em.N8Z6Tspby/h/j3Jszxg$DJbLt.qrf9TUIuozNNcB/i/5buMLXmZH01aEb4VswHA",
    "manager": "$pbkdf2-sha256$29000$BcD4/9.bM.YcQ8h5L.U8Rw$ROmOE5nHgGV/yGt9JVZErLeiZ1Rs6v2zW6.MGCzmZEM",
    "alice": "$pbkdf2-sha256$29000$ZIwRYqxVSmmtFQIgJOQ85w$iH9ooAMiN7AuchDq.nyKOj8NC1wjYdedHNPcPPgXCLM",
    "bob": "$pbkdf2-sha256$29000$Y6xVqvUeg5DyHqO0tjaGMA$d1upAmoOidtFr0Fyqn9PVlHKAUM805IygM4rnJFf.9s",
}


def _permission_id(code: str) -> str:
    return f"PERM-{code.upper().replace(':', '-') }"


def _upsert(session: Session, model: type[object], identifier: str, **values: object) -> None:
    record = session.get(model, identifier)
    if record is None:
        session.add(model(id=identifier, **values))
        return

    for field, value in values.items():
        setattr(record, field, value)


def _seed_organization_and_roles(session: Session) -> None:
    _upsert(
        session,
        Organization,
        DEMO_ORGANIZATION_ID,
        name="Demo Security Company",
    )

    for role_name, role_id in ROLE_IDS.items():
        _upsert(session, Role, role_id, name=role_name)

    for code in PERMISSION_CODES:
        _upsert(
            session,
            Permission,
            _permission_id(code),
            code=code,
            description=f"Allows {code}",
        )


def _seed_role_permissions(session: Session) -> None:
    role_ids = tuple(ROLE_IDS.values())
    session.query(RolePermission).filter(RolePermission.role_id.in_(role_ids)).delete(
        synchronize_session=False,
    )

    for role_name, permission_codes in ROLE_PERMISSION_CODES.items():
        for code in permission_codes:
            session.add(
                RolePermission(
                    role_id=ROLE_IDS[role_name],
                    permission_id=_permission_id(code),
                ),
            )


def _seed_users_and_scopes(session: Session) -> None:
    _upsert(
        session,
        Zone,
        ZONE_A_ID,
        name="Zone A - Main Lobby",
        organization_id=DEMO_ORGANIZATION_ID,
    )
    _upsert(
        session,
        Zone,
        ZONE_B_ID,
        name="Zone B - Parking",
        organization_id=DEMO_ORGANIZATION_ID,
    )

    users = (
        ("admin", "Admin", RoleName.ADMIN, None),
        ("manager", "Manager", RoleName.MANAGER, USER_IDS["admin"]),
        ("alice", "Alice", RoleName.OPERATOR, USER_IDS["manager"]),
        ("bob", "Bob", RoleName.OPERATOR, USER_IDS["manager"]),
    )
    for username, display_name, role_name, manager_id in users:
        _upsert(
            session,
            User,
            USER_IDS[username],
            username=username,
            password_hash=PASSWORD_HASHES[username],
            display_name=display_name,
            organization_id=DEMO_ORGANIZATION_ID,
            role_id=ROLE_IDS[role_name],
            manager_id=manager_id,
            is_active=True,
        )

    user_ids = tuple(USER_IDS.values())
    session.query(UserZoneScope).filter(UserZoneScope.user_id.in_(user_ids)).delete(
        synchronize_session=False,
    )

    scopes = (
        ("admin", ZONE_A_ID, "admin"),
        ("admin", ZONE_B_ID, "admin"),
        ("manager", ZONE_A_ID, "admin"),
        ("manager", ZONE_B_ID, "admin"),
        ("alice", ZONE_A_ID, "manager"),
        ("bob", ZONE_B_ID, "manager"),
    )
    for username, zone_id, assigned_by_username in scopes:
        session.add(
            UserZoneScope(
                user_id=USER_IDS[username],
                zone_id=zone_id,
                assigned_by_user_id=USER_IDS[assigned_by_username],
                created_at=datetime(2025, 1, 1, 8, 0, 0),
            ),
        )


def _seed_cameras_and_events(session: Session) -> None:
    cameras = (
        ("CAM-A01", "Main Entrance", ZONE_A_ID, CameraStatus.ONLINE),
        ("CAM-A02", "Reception", ZONE_A_ID, CameraStatus.ONLINE),
        ("CAM-B01", "Parking Gate", ZONE_B_ID, CameraStatus.OFFLINE),
        ("CAM-B02", "Basement", ZONE_B_ID, CameraStatus.ONLINE),
    )
    for camera_id, name, zone_id, status in cameras:
        _upsert(
            session,
            Camera,
            camera_id,
            name=name,
            organization_id=DEMO_ORGANIZATION_ID,
            zone_id=zone_id,
            status=status,
        )

    events = (
        ("EVT-A01-001", "CAM-A01", "person_detected", datetime(2025, 1, 15, 9, 0), "Person detected at Main Entrance."),
        ("EVT-A01-002", "CAM-A01", "intrusion_detected", datetime(2025, 1, 15, 9, 15), "Intrusion detected at Main Entrance."),
        ("EVT-A02-001", "CAM-A02", "person_detected", datetime(2025, 1, 15, 9, 30), "Person detected at Reception."),
        ("EVT-B01-001", "CAM-B01", "vehicle_detected", datetime(2025, 1, 15, 10, 0), "Vehicle detected at Parking Gate."),
        ("EVT-B01-002", "CAM-B01", "intrusion_detected", datetime(2025, 1, 15, 10, 15), "Intrusion detected at Parking Gate."),
        ("EVT-B02-001", "CAM-B02", "person_detected", datetime(2025, 1, 15, 10, 30), "Person detected at Basement."),
    )
    for event_id, camera_id, event_type, occurred_at, description in events:
        _upsert(
            session,
            Event,
            event_id,
            camera_id=camera_id,
            recording_id=None,
            event_type=event_type,
            occurred_at=occurred_at,
            description=description,
            start_offset_ms=None,
            end_offset_ms=None,
            confidence=None,
            snapshot_path=None,
            clip_path=None,
            image_url=None,
            video_url=None,
        )


SessionFactory = Callable[[], Session]


def seed_database(session_factory: SessionFactory = SessionLocal) -> None:
    """Idempotently create or update deterministic demo rows without touching media files."""
    with session_factory.begin() as session:
        _seed_organization_and_roles(session)
        session.flush()
        _seed_role_permissions(session)
        _seed_users_and_scopes(session)
        session.flush()
        _seed_cameras_and_events(session)


def main() -> None:
    create_all()
    seed_database()
    print("Seeded deterministic demo data.")


if __name__ == "__main__":
    main()
