from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine, get_db
from app.main import app
from app.models import AuditLog
from app.seed import USER_IDS, seed_database


@pytest.fixture
def client(tmp_path):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'audit-api-test.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(session_factory)
    with session_factory.begin() as session:
        for audit_id, username, decision in (
            ("AUDIT-ADMIN", "admin", "ALLOW"),
            ("AUDIT-MANAGER", "manager", "ALLOW"),
            ("AUDIT-ALICE", "alice", "DENY"),
            ("AUDIT-BOB", "bob", "ALLOW"),
        ):
            session.add(
                AuditLog(
                    id=audit_id,
                    request_id=f"REQ-{audit_id}",
                    user_id=USER_IDS[username],
                    action="media:view_video",
                    resource_type="media",
                    resource_id="EVT-B01-001",
                    decision=decision,
                    reason="resource_out_of_scope" if decision == "DENY" else "allowed",
                    stage="PRE_AUTHORIZATION",
                    created_at=datetime(2025, 1, 20, 9, 0),
                ),
            )

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


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_sees_organization_audit(client: TestClient):
    response = client.get("/api/v1/audit", headers=auth_headers(client, "admin", "admin123"))

    assert response.status_code == 200
    assert {record["user"] for record in response.json()} == {"admin", "manager", "alice", "bob"}


def test_manager_sees_own_and_managed_operator_audit_only(client: TestClient):
    response = client.get("/api/v1/audit", headers=auth_headers(client, "manager", "manager123"))

    assert response.status_code == 200
    assert {record["user"] for record in response.json()} == {"manager", "alice", "bob"}
    assert {record["decision"] for record in response.json()} == {"ALLOW", "DENY"}


def test_operator_is_denied_audit_access(client: TestClient):
    response = client.get("/api/v1/audit", headers=auth_headers(client, "alice", "alice123"))

    assert response.status_code == 403
