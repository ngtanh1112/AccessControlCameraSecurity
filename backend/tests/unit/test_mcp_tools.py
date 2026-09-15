from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine
from app.main import app
from app.mcp.registry import MCPToolRegistry, create_default_registry
from app.mcp.tools import access_control, media, search, system_log
from app.models import AuditLog
from app.security import audit, authorization
from app.security.context import SecurityContext
from app.security.gateway import AccessDenied
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
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'mcp-tool-test.db'}")
    Base.metadata.create_all(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(factory)
    monkeypatch.setattr(authorization, "SessionLocal", factory)
    monkeypatch.setattr(audit, "SessionLocal", factory)
    monkeypatch.setattr(access_control, "SessionLocal", factory)
    monkeypatch.setattr(search, "SessionLocal", factory)
    monkeypatch.setattr(media, "SessionLocal", factory)
    monkeypatch.setattr(system_log, "SessionLocal", factory)
    yield factory
    database_engine.dispose()


def alice_context() -> SecurityContext:
    return SecurityContext(
        request_id=str(uuid4()),
        user_id=USER_IDS["alice"],
        username="alice",
        organization_id=DEMO_ORGANIZATION_ID,
        role="OPERATOR",
        permissions=ALICE_PERMISSIONS,
        allowed_zone_ids={"ZONE-A"},
    )


def test_registry_register_get_and_list():
    registry = MCPToolRegistry()
    default_registry = create_default_registry()

    assert registry.list() == []
    assert default_registry.get("search_events") is not None
    assert {tool.name for tool in default_registry.list()} == {
        "can_access",
        "create_alert",
        "filter_camera_ids",
        "get_event",
        "get_event_image",
        "get_event_video",
        "get_live_camera",
        "get_my_cameras",
        "get_my_permissions",
        "get_my_zones",
        "search_events",
        "search_system_logs",
    }


def test_registry_endpoint_exposes_tool_metadata():
    with TestClient(app) as client:
        response = client.get("/api/v1/registry/tools")

    assert response.status_code == 200
    metadata = {tool["name"]: tool for tool in response.json()}
    assert metadata["search_events"]["required_permission"] == "event:search"
    assert metadata["get_event_video"]["required_permission"] == "media:view_video"


def test_direct_forbidden_mcp_video_tool_is_denied_by_gateway(seeded_database):
    context = alice_context()
    tool = create_default_registry().get("get_event_video")
    assert tool is not None

    with pytest.raises(AccessDenied) as error:
        tool.execute(context, {"event_id": "EVT-B01-001"})

    assert error.value.decision.reason == "resource_out_of_scope"
    with seeded_database() as session:
        audit_log = session.scalar(select(AuditLog).where(AuditLog.request_id == context.request_id))
        assert audit_log is not None
        assert audit_log.decision == "DENY"
        assert audit_log.stage == "TOOL_ENFORCEMENT"


def test_mcp_search_and_camera_tools_are_server_side_scoped(seeded_database):
    context = alice_context()
    registry = create_default_registry()
    cameras = registry.get("get_my_cameras")
    search_events = registry.get("search_events")
    assert cameras is not None
    assert search_events is not None

    camera_result = cameras.execute(context, {})
    event_result = search_events.execute(context, {})

    assert [camera["id"] for camera in camera_result] == ["CAM-A01", "CAM-A02"]
    assert [event["id"] for event in event_result] == [
        "EVT-A01-001",
        "EVT-A01-002",
        "EVT-A02-001",
    ]


def test_scope_filter_returns_scope_or_denies_explicit_forbidden_camera(seeded_database):
    context = alice_context()
    tool = create_default_registry().get("filter_camera_ids")
    assert tool is not None

    assert tool.execute(context, {}) == ["CAM-A01", "CAM-A02"]
    assert tool.execute(context, {"camera_ids": ["CAM-A02"]}) == ["CAM-A02"]
    with pytest.raises(AccessDenied):
        tool.execute(context, {"camera_ids": ["CAM-B01"]})


def test_mcp_media_tool_allows_authorized_event_after_gateway_check(seeded_database):
    context = alice_context()
    tool = create_default_registry().get("get_event_image")
    assert tool is not None

    result = tool.execute(context, {"event_id": "EVT-A01-001"})

    assert result == {
        "event_id": "EVT-A01-001",
        "url": "mock://events/EVT-A01-001/image",
        "is_mock": True,
    }
