from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.v1 import iva
from app.db import Base, create_database_engine, get_db
from app.main import app
from app.mcp.tools import search
from app.security import audit, authorization, execution_trace
from app.seed import seed_database
from app.services.video_analyzer import FakeVideoAnalyzer


@pytest.fixture
def client_and_fake(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'iva-fake-test.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(session_factory)
    fake_analyzer = FakeVideoAnalyzer()
    monkeypatch.setenv("VIDEO_ANALYZER_MODE", "fake")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "private-media"))
    monkeypatch.setattr(iva, "create_video_analyzer", lambda: fake_analyzer)
    monkeypatch.setattr(authorization, "SessionLocal", session_factory)
    monkeypatch.setattr(audit, "SessionLocal", session_factory)
    monkeypatch.setattr(execution_trace, "SessionLocal", session_factory)
    monkeypatch.setattr(search, "SessionLocal", session_factory)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, fake_analyzer
    app.dependency_overrides.clear()
    database_engine.dispose()


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_fake_ingest_persists_searchable_events_without_running_yolo(client_and_fake):
    client, fake_analyzer = client_and_fake
    admin_headers = auth_headers(client, "admin", "admin123")
    upload = client.post(
        "/api/v1/iva/recordings",
        data={"camera_id": "CAM-A01", "recording_started_at": "2025-02-01T09:00:00"},
        files={"file": ("fixture.mp4", b"not-a-real-video", "video/mp4")},
        headers=admin_headers,
    )

    assert upload.status_code == 200
    recording_id = upload.json()["recording_id"]
    assert upload.json()["status"] == "PENDING"

    analysis = client.post(f"/api/v1/iva/recordings/{recording_id}/analyze", headers=admin_headers)

    assert analysis.status_code == 200
    assert analysis.json()["status"] == "COMPLETED"
    assert fake_analyzer.calls == 1
    events = analysis.json()["events"]
    assert [(event["event_type"], event["start_offset_ms"], event["end_offset_ms"], event["confidence"]) for event in events] == [
        ("person_detected", 10_000, 15_000, 0.91),
        ("vehicle_detected", 40_000, 45_000, 0.87),
    ]
    assert all(event["recording_id"] == recording_id for event in events)
    assert all(event["snapshot_url"] is not None for event in events)

    alice_events = client.get(f"/api/v1/events?recording_id={recording_id}", headers=auth_headers(client, "alice", "alice123"))
    bob_events = client.get(f"/api/v1/events?recording_id={recording_id}", headers=auth_headers(client, "bob", "bob123"))
    assert alice_events.status_code == 200
    assert len(alice_events.json()) == 2
    assert bob_events.status_code == 200
    assert bob_events.json() == []

    alice_image = client.get(events[0]["snapshot_url"], headers=auth_headers(client, "alice", "alice123"))
    bob_image = client.get(events[0]["snapshot_url"], headers=auth_headers(client, "bob", "bob123"))
    assert alice_image.status_code == 200
    assert alice_image.headers["content-type"].startswith("image/jpeg")
    assert bob_image.status_code == 403

    conversation = client.post(
        "/api/v1/conversations/messages",
        json={"message": f"CAM-A01 từ 00:40 đến 01:00 REC-{recording_id[4:]} có gì?"},
        headers=auth_headers(client, "alice", "alice123"),
    )
    assert conversation.status_code == 200
    assert conversation.json()["decision"] == "ALLOW"
    assert [event["event_type"] for event in conversation.json()["data"]] == ["vehicle_detected"]
    assert fake_analyzer.calls == 1

    denied = client.post(
        "/api/v1/conversations/messages",
        json={"message": f"CAM-A01 từ 00:40 đến 01:00 REC-{recording_id[4:]} có gì?"},
        headers=auth_headers(client, "bob", "bob123"),
    )
    assert denied.status_code == 200
    assert denied.json()["pre_authorization"] == "DENY"
    assert denied.json()["agent_invoked"] is False
    assert fake_analyzer.calls == 1


def test_upload_rejects_non_mp4_and_operator_is_denied(client_and_fake):
    client, _ = client_and_fake
    admin_headers = auth_headers(client, "admin", "admin123")
    invalid = client.post(
        "/api/v1/iva/recordings",
        data={"camera_id": "CAM-A01", "recording_started_at": datetime.now().isoformat()},
        files={"file": ("fixture.avi", b"invalid", "video/x-msvideo")},
        headers=admin_headers,
    )
    denied = client.get("/api/v1/iva/recordings", headers=auth_headers(client, "alice", "alice123"))

    assert invalid.status_code == 422
    assert denied.status_code == 403


def test_analysis_failure_never_leaves_recording_analyzing(client_and_fake, monkeypatch):
    client, _ = client_and_fake

    class FailingAnalyzer:
        def analyze(self, recording):
            raise RuntimeError("fixture analyzer failure")

    monkeypatch.setattr(iva, "create_video_analyzer", lambda: FailingAnalyzer())
    admin_headers = auth_headers(client, "admin", "admin123")
    upload = client.post(
        "/api/v1/iva/recordings",
        data={"camera_id": "CAM-A01", "recording_started_at": "2025-02-01T09:00:00"},
        files={"file": ("fixture.mp4", b"not-a-real-video", "video/mp4")},
        headers=admin_headers,
    )
    recording_id = upload.json()["recording_id"]

    analysis = client.post(f"/api/v1/iva/recordings/{recording_id}/analyze", headers=admin_headers)
    recording = client.get(f"/api/v1/iva/recordings/{recording_id}", headers=admin_headers)

    assert analysis.status_code == 500
    assert recording.json()["status"] == "FAILED"
