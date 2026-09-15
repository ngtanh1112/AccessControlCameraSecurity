from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine
from app.models import AuditLog, Camera, CameraStatus, Organization, Zone
from app.security import audit, authorization
from app.security.authorization import authorize
from app.security.context import SecurityContext
from app.security.gateway import AccessControlGateway, AccessDenied
from app.seed import DEMO_ORGANIZATION_ID, USER_IDS, seed_database


ALICE_PERMISSIONS = {
    "camera:list",
    "camera:view_live",
    "event:search",
    "event:view",
    "media:view_image",
    "media:view_video",
    "alert:create",
}


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'authorization-test.db'}")
    Base.metadata.create_all(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(factory)
    monkeypatch.setattr(authorization, "SessionLocal", factory)
    monkeypatch.setattr(audit, "SessionLocal", factory)
    yield factory
    database_engine.dispose()


def context_for(username: str) -> SecurityContext:
    contexts = {
        "alice": SecurityContext(
            request_id=str(uuid4()),
            user_id=USER_IDS["alice"],
            username="alice",
            organization_id=DEMO_ORGANIZATION_ID,
            role="OPERATOR",
            permissions=ALICE_PERMISSIONS,
            allowed_zone_ids={"ZONE-A"},
        ),
        "bob": SecurityContext(
            request_id=str(uuid4()),
            user_id=USER_IDS["bob"],
            username="bob",
            organization_id=DEMO_ORGANIZATION_ID,
            role="OPERATOR",
            permissions=ALICE_PERMISSIONS,
            allowed_zone_ids={"ZONE-B"},
        ),
        "manager": SecurityContext(
            request_id=str(uuid4()),
            user_id=USER_IDS["manager"],
            username="manager",
            organization_id=DEMO_ORGANIZATION_ID,
            role="MANAGER",
            permissions=ALICE_PERMISSIONS | {"operator:manage", "scope:assign", "system_log:view", "audit:view"},
            allowed_zone_ids={"ZONE-A"},
        ),
        "admin": SecurityContext(
            request_id=str(uuid4()),
            user_id=USER_IDS["admin"],
            username="admin",
            organization_id=DEMO_ORGANIZATION_ID,
            role="ADMIN",
            permissions=ALICE_PERMISSIONS | {"operator:manage", "scope:assign", "system_log:view", "audit:view", "system:admin"},
            allowed_zone_ids=set(),
        ),
    }
    return contexts[username]


@pytest.mark.parametrize(
    ("username", "camera_id", "allowed"),
    [
        ("alice", "CAM-A01", True),
        ("alice", "CAM-B01", False),
        ("bob", "CAM-B01", True),
        ("bob", "CAM-A01", False),
    ],
)
def test_operator_camera_scope(seeded_database, username, camera_id, allowed):
    decision = authorize(context_for(username), "camera:view_live", "camera", camera_id)

    assert decision.allowed is allowed
    assert decision.reason == ("allowed" if allowed else "resource_out_of_scope")


def test_event_scope_resolves_event_camera_zone(seeded_database):
    decision = authorize(context_for("alice"), "event:view", "event", "EVT-B01-001")

    assert decision.allowed is False
    assert decision.reason == "resource_out_of_scope"
    assert decision.resource_type == "event"
    assert decision.resource_id == "EVT-B01-001"


def test_media_scope_resolves_event_camera_zone(seeded_database):
    decision = authorize(context_for("alice"), "media:view_video", "media", "EVT-B01-001")

    assert decision.allowed is False
    assert decision.reason == "resource_out_of_scope"


def test_search_returns_only_operator_scoped_cameras(seeded_database):
    decision = authorize(context_for("alice"), "event:search", "event")

    assert decision.allowed is True
    assert decision.allowed_zone_ids == ["ZONE-A"]
    assert decision.allowed_camera_ids == ["CAM-A01", "CAM-A02"]


def test_admin_has_full_camera_scope_inside_organization(seeded_database):
    context = context_for("admin")
    search_decision = authorize(context, "camera:list", "camera")

    assert search_decision.allowed is True
    assert search_decision.allowed_zone_ids == ["ZONE-A", "ZONE-B"]
    assert search_decision.allowed_camera_ids == ["CAM-A01", "CAM-A02", "CAM-B01", "CAM-B02"]
    for camera_id in search_decision.allowed_camera_ids:
        assert authorize(context, "camera:view_live", "camera", camera_id).allowed is True


def test_manager_remains_limited_to_its_allowed_zones(seeded_database):
    decision = authorize(context_for("manager"), "camera:view_live", "camera", "CAM-B01")

    assert decision.allowed is False
    assert decision.reason == "resource_out_of_scope"


def test_missing_permission_is_denied(seeded_database):
    context = context_for("alice")
    decision = authorize(context, "system:admin", "camera", "CAM-A01")

    assert decision.allowed is False
    assert decision.reason == "permission_missing"
    assert decision.allowed_zone_ids == []
    assert decision.allowed_camera_ids == []


def test_admin_cannot_cross_organization_boundary(seeded_database):
    with authorization.SessionLocal.begin() as session:
        session.add(Organization(id="ORG-OTHER", name="Other Organization"))
        session.add(Zone(id="ZONE-OTHER", name="Other Zone", organization_id="ORG-OTHER"))
        session.add(
            Camera(
                id="CAM-OTHER",
                name="Other Camera",
                organization_id="ORG-OTHER",
                zone_id="ZONE-OTHER",
                status=CameraStatus.ONLINE,
            ),
        )

    decision = authorize(context_for("admin"), "camera:view_live", "camera", "CAM-OTHER")

    assert decision.allowed is False
    assert decision.reason == "organization_mismatch"


def test_gateway_audits_allow_and_deny(seeded_database):
    gateway = AccessControlGateway()
    allowed_context = context_for("alice")
    denied_context = context_for("alice")

    result = gateway.execute(
        allowed_context,
        "camera:view_live",
        "camera",
        "CAM-A01",
        lambda decision: decision.resource_id,
        stage="DIRECT_API",
    )
    assert result == "CAM-A01"

    with pytest.raises(AccessDenied) as error:
        gateway.execute(
            denied_context,
            "camera:view_live",
            "camera",
            "CAM-B01",
            lambda _decision: pytest.fail("Denied operation must not run"),
        )
    assert error.value.decision.reason == "resource_out_of_scope"

    with audit.SessionLocal() as session:
        rows = session.scalars(select(AuditLog).order_by(AuditLog.created_at)).all()
        assert [(row.decision, row.stage) for row in rows] == [
            ("ALLOW", "DIRECT_API"),
            ("DENY", "TOOL_ENFORCEMENT"),
        ]
        assert session.scalar(select(func.count(AuditLog.id))) == 2
