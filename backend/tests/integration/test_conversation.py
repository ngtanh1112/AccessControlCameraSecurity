from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine, get_db
from app.main import app
from app.mcp.tools import access_control, media, search, system_log
from app.models import ExecutionTrace
from app.security import audit, authorization, execution_trace
from app.seed import seed_database
from app.services.search_service import SearchService


@pytest.fixture
def client_and_factory(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'conversation-test.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(session_factory)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(authorization, "SessionLocal", session_factory)
    monkeypatch.setattr(audit, "SessionLocal", session_factory)
    monkeypatch.setattr(execution_trace, "SessionLocal", session_factory)
    monkeypatch.setattr(access_control, "SessionLocal", session_factory)
    monkeypatch.setattr(search, "SessionLocal", session_factory)
    monkeypatch.setattr(media, "SessionLocal", session_factory)
    monkeypatch.setattr(system_log, "SessionLocal", session_factory)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    database_engine.dispose()


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def send(client: TestClient, headers: dict[str, str], message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/conversations/messages",
        json={"message": message},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def trace_for(factory, request_id: str) -> ExecutionTrace:
    with factory() as session:
        trace = session.scalar(select(ExecutionTrace).where(ExecutionTrace.request_id == request_id))
    assert trace is not None
    return trace


def test_alice_camera_prompt_uses_agent_mcp_and_gateway(client_and_factory):
    client, factory = client_and_factory
    body = send(
        client,
        auth_headers(client, "alice", "alice123"),
        "Camera nào tôi được xem?",
    )

    assert body["intent"] == "LIST_MY_CAMERAS"
    assert body["pre_authorization"] == "ALLOW"
    assert body["agent"] == "SearchCameraSubAgent"
    assert body["tool"] == "get_my_cameras"
    assert body["decision"] == "ALLOW"
    assert [camera["id"] for camera in body["data"]] == ["CAM-A01", "CAM-A02"]
    trace = trace_for(factory, body["request_id"])
    assert (trace.agent_invoked, trace.mcp_invoked, trace.backend_invoked) == (True, True, True)


def test_alice_event_search_stays_in_zone_a(client_and_factory):
    client, _ = client_and_factory
    body = send(
        client,
        auth_headers(client, "alice", "alice123"),
        "Tìm tất cả sự kiện",
    )

    assert body["intent"] == "SEARCH_EVENT"
    assert body["decision"] == "ALLOW"
    assert {event["camera_id"] for event in body["data"]} == {"CAM-A01", "CAM-A02"}
    assert {event["event_id"] for event in body["data"]} == {
        "EVT-A01-001",
        "EVT-A01-002",
        "EVT-A02-001",
    }


def test_camera_time_range_reaches_search_service(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    captured: dict[str, object] = {}

    def capture_search(self, allowed_camera_ids, **filters):
        captured["allowed_camera_ids"] = allowed_camera_ids
        captured.update(filters)
        return []

    monkeypatch.setattr(SearchService, "search_events", capture_search)
    body = send(
        client,
        auth_headers(client, "alice", "alice123"),
        "CAM-A01 từ 00:40 đến 01:00 có gì?",
    )

    assert body["pre_authorization"] == "ALLOW"
    assert body["decision"] == "ALLOW"
    assert body["agent"] == "SearchCameraSubAgent"
    assert body["tool"] == "search_events"
    assert body["mcp_invoked"] is True
    assert body["backend_invoked"] is True
    assert captured == {
        "allowed_camera_ids": ["CAM-A01", "CAM-A02"],
        "camera_id": "CAM-A01",
        "recording_id": None,
        "event_type": None,
        "from_time": None,
        "to_time": None,
        "start_offset_ms": 40_000,
        "end_offset_ms": 60_000,
    }


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("CAM-B01 từ 00:40 đến 01:00 có gì?", "SEARCH_EVENT"),
        ("Cho tôi xem video EVT-B01-001", "VIEW_VIDEO"),
    ],
)
def test_alice_forbidden_prompts_early_deny_before_agent_mcp_or_backend(
    client_and_factory,
    message,
    intent,
):
    client, factory = client_and_factory
    body = send(client, auth_headers(client, "alice", "alice123"), message)

    assert body == {
        "request_id": body["request_id"],
        "intent": intent,
        "pre_authorization": "DENY",
        "agent_invoked": False,
        "agent": None,
        "mcp_invoked": False,
        "tool": None,
        "backend_invoked": False,
        "decision": "DENY",
        "answer": "Bạn không có quyền truy cập tài nguyên này.",
        "data": None,
    }
    trace = trace_for(factory, body["request_id"])
    assert (trace.agent_invoked, trace.mcp_invoked, trace.backend_invoked) == (False, False, False)


def test_manager_event_search_includes_both_scopes(client_and_factory):
    client, _ = client_and_factory
    body = send(
        client,
        auth_headers(client, "manager", "manager123"),
        "Tìm tất cả sự kiện",
    )

    assert body["decision"] == "ALLOW"
    assert {event["camera_id"] for event in body["data"]} == {
        "CAM-A01",
        "CAM-A02",
        "CAM-B01",
        "CAM-B02",
    }
