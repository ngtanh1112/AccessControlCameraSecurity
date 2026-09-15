from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine, get_db
from app.main import app
from app.models import Event, VideoAnalysisStatus, VideoRecording
from app.security import audit, authorization
from app.seed import seed_database


@pytest.fixture
def client_and_factory(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'resource-api-test.db'}")
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


def test_alice_receives_only_zone_a_cameras_and_events(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    cameras = client.get("/api/v1/cameras", headers=headers)
    events = client.get("/api/v1/events", headers=headers)
    camera_events = client.get("/api/v1/events?camera_id=CAM-A01", headers=headers)

    assert cameras.status_code == 200
    assert [camera["id"] for camera in cameras.json()] == ["CAM-A01", "CAM-A02"]
    assert events.status_code == 200
    assert [event["id"] for event in events.json()] == [
        "EVT-A01-001",
        "EVT-A01-002",
        "EVT-A02-001",
    ]
    assert [event["id"] for event in camera_events.json()] == [
        "EVT-A01-001",
        "EVT-A01-002",
    ]


def test_forbidden_alice_direct_accesses_return_403(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    responses = [
        client.get("/api/v1/events/EVT-B01-001", headers=headers),
        client.get("/api/v1/media/events/EVT-B01-001/image", headers=headers),
        client.get("/api/v1/media/events/EVT-B01-001/video", headers=headers),
        client.get("/api/v1/media/cameras/CAM-B01/live", headers=headers),
        client.get("/api/v1/events?camera_id=CAM-B01", headers=headers),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403, 403]


def test_seed_event_media_is_protected_and_returns_mock_data(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    response = client.get("/api/v1/media/events/EVT-A01-001/image", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "event_id": "EVT-A01-001",
        "url": "mock://events/EVT-A01-001/image",
        "is_mock": True,
    }


def test_absolute_time_filtering_uses_occurred_at(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    response = client.get(
        "/api/v1/events",
        params={
            "from_time": "2025-01-15T09:10:00",
            "to_time": "2025-01-15T09:20:00",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == ["EVT-A01-002"]


def test_offset_filters_require_recording_id(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    response = client.get(
        "/api/v1/events",
        params={"start_offset_ms": 100},
        headers=headers,
    )

    assert response.status_code == 422
    assert "recording_id is required" in response.json()["detail"]


def test_offset_filters_use_selected_recording_and_interval_overlap(client_and_factory):
    client, session_factory = client_and_factory
    with session_factory.begin() as session:
        session.add(
            VideoRecording(
                id="REC-A01-TEST",
                camera_id="CAM-A01",
                original_filename="fixture.mp4",
                stored_path="data/videos/fixture.mp4",
                recording_started_at=datetime(2025, 1, 16, 9, 0),
                duration_ms=10_000,
                analysis_status=VideoAnalysisStatus.COMPLETED,
                analyzed_at=datetime(2025, 1, 16, 9, 1),
                model_name=None,
                created_at=datetime(2025, 1, 16, 9, 0),
            ),
        )
        session.add_all(
            [
                Event(
                    id="EVT-OFFSET-ONE",
                    camera_id="CAM-A01",
                    recording_id="REC-A01-TEST",
                    event_type="person_detected",
                    occurred_at=datetime(2025, 1, 16, 9, 0, 0, 100_000),
                    description="Offset fixture one",
                    start_offset_ms=100,
                    end_offset_ms=200,
                    confidence=0.9,
                    snapshot_path=None,
                    clip_path=None,
                    image_url=None,
                    video_url=None,
                ),
                Event(
                    id="EVT-OFFSET-TWO",
                    camera_id="CAM-A01",
                    recording_id="REC-A01-TEST",
                    event_type="person_detected",
                    occurred_at=datetime(2025, 1, 16, 9, 0, 0, 300_000),
                    description="Offset fixture two",
                    start_offset_ms=300,
                    end_offset_ms=400,
                    confidence=0.9,
                    snapshot_path=None,
                    clip_path=None,
                    image_url=None,
                    video_url=None,
                ),
            ],
        )

    headers = auth_headers(client, "alice", "alice123")
    response = client.get(
        "/api/v1/events",
        params={
            "recording_id": "REC-A01-TEST",
            "start_offset_ms": 150,
            "end_offset_ms": 250,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == ["EVT-OFFSET-ONE"]


def test_bob_has_inverse_scope_and_admin_sees_all_cameras(client_and_factory):
    client, _ = client_and_factory
    bob_headers = auth_headers(client, "bob", "bob123")
    admin_headers = auth_headers(client, "admin", "admin123")

    bob_events = client.get("/api/v1/events", headers=bob_headers)
    admin_cameras = client.get("/api/v1/cameras", headers=admin_headers)

    assert [event["id"] for event in bob_events.json()] == [
        "EVT-B01-001",
        "EVT-B01-002",
        "EVT-B02-001",
    ]
    assert [camera["id"] for camera in admin_cameras.json()] == [
        "CAM-A01",
        "CAM-A02",
        "CAM-B01",
        "CAM-B02",
    ]
