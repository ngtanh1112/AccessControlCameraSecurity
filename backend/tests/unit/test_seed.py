from __future__ import annotations

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import sessionmaker
import pytest

from app.db import Base, create_database_engine
from app.models import Camera, Event, Permission, Role, RoleName, RolePermission, User, UserZoneScope
from app.seed import seed_database


@pytest.fixture
def seeded_database(tmp_path):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'seed-test.db'}")
    Base.metadata.create_all(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(factory)
    yield database_engine, factory
    database_engine.dispose()


def user_zone_names(session, username: str) -> set[str]:
    user = session.scalar(select(User).where(User.username == username))
    assert user is not None
    return {scope.zone.name for scope in user.zone_scopes}


def test_seed_roles_and_scopes(seeded_database):
    _, factory = seeded_database

    with factory() as session:
        roles = set(session.scalars(select(Role.name)).all())
        assert roles == {RoleName.ADMIN, RoleName.MANAGER, RoleName.OPERATOR}
        assert session.scalar(select(func.count(Role.id))) == 3
        assert set(session.scalars(select(User.username)).all()) == {
            "admin",
            "manager",
            "alice",
            "bob",
        }
        assert session.scalar(select(func.count(Permission.id))) == 12
        assert user_zone_names(session, "alice") == {"Zone A - Main Lobby"}
        assert user_zone_names(session, "bob") == {"Zone B - Parking"}
        assert user_zone_names(session, "manager") == {
            "Zone A - Main Lobby",
            "Zone B - Parking",
        }


def test_seed_event_camera_zone_relationships(seeded_database):
    _, factory = seeded_database
    expected_event_resources = {
        "EVT-A01-001": ("CAM-A01", "Zone A - Main Lobby"),
        "EVT-A01-002": ("CAM-A01", "Zone A - Main Lobby"),
        "EVT-A02-001": ("CAM-A02", "Zone A - Main Lobby"),
        "EVT-B01-001": ("CAM-B01", "Zone B - Parking"),
        "EVT-B01-002": ("CAM-B01", "Zone B - Parking"),
        "EVT-B02-001": ("CAM-B02", "Zone B - Parking"),
    }

    with factory() as session:
        events = session.scalars(select(Event)).all()
        assert {
            event.id: (event.camera.id, event.camera.zone.name) for event in events
        } == expected_event_resources
        assert all(event.recording_id is None for event in events)
        assert all(event.start_offset_ms is None for event in events)
        assert all(event.end_offset_ms is None for event in events)
        assert all(event.confidence is None for event in events)


def test_video_recording_table_exists(seeded_database):
    database_engine, _ = seeded_database

    inspector = inspect(database_engine)
    assert "video_recordings" in inspector.get_table_names()
    event_columns = {column["name"] for column in inspector.get_columns("events")}
    assert {
        "recording_id",
        "start_offset_ms",
        "end_offset_ms",
        "confidence",
        "snapshot_path",
        "clip_path",
    }.issubset(event_columns)


def test_seed_is_idempotent(seeded_database):
    _, factory = seeded_database
    seed_database(factory)

    with factory() as session:
        assert session.scalar(select(func.count(Role.id))) == 3
        assert session.scalar(select(func.count(Permission.id))) == 12
        assert session.scalar(select(func.count(RolePermission.role_id))) == 30
        assert session.scalar(select(func.count(User.id))) == 4
        assert session.scalar(select(func.count(Camera.id))) == 4
        assert session.scalar(select(func.count(Event.id))) == 6
        assert session.scalar(select(func.count(UserZoneScope.user_id))) == 6
