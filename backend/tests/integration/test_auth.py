from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine, get_db
from app.main import app
from app.seed import seed_database


@pytest.fixture
def client(tmp_path):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'auth-test.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(session_factory)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    database_engine.dispose()


def login_alice(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "alice123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    return body["access_token"]


def test_alice_login_returns_small_jwt_payload(client: TestClient):
    access_token = login_alice(client)

    payload = jwt.get_unverified_claims(access_token)
    assert set(payload) == {"sub", "username", "org_id", "exp"}
    assert payload["username"] == "alice"
    assert payload["org_id"] == "ORG-DEMO"
    assert "permissions" not in payload
    assert "zones" not in payload


def test_wrong_password_returns_401(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_auth_me_returns_alice_security_data(client: TestClient):
    access_token = login_alice(client)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["display_name"] == "Alice"
    assert body["role"] == "OPERATOR"
    assert body["manager"] == {"id": "USER-MANAGER", "username": "manager"}
    assert body["zones"] == [{"id": "ZONE-A", "name": "Zone A - Main Lobby"}]
    assert body["permissions"] == [
        "alert:create",
        "camera:list",
        "camera:view_live",
        "event:search",
        "event:view",
        "media:view_image",
        "media:view_video",
    ]
