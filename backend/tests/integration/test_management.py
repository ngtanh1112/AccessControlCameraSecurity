from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine, get_db
from app.main import app
from app.models import User, UserZoneScope, Zone
from app.security import audit, authorization
from app.seed import DEMO_ORGANIZATION_ID, PASSWORD_HASHES, USER_IDS, seed_database


OTHER_MANAGER_ID = "USER-OTHER-MANAGER"
CHARLIE_ID = "USER-CHARLIE"
ZONE_C_ID = "ZONE-C"


@pytest.fixture
def client_and_factory(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'management-test.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(session_factory)

    with session_factory.begin() as session:
        session.add(Zone(id=ZONE_C_ID, name="Zone C - Warehouse", organization_id=DEMO_ORGANIZATION_ID))
        session.add(
            User(
                id=OTHER_MANAGER_ID,
                username="other-manager",
                password_hash=PASSWORD_HASHES["manager"],
                display_name="Other Manager",
                organization_id=DEMO_ORGANIZATION_ID,
                role_id="ROLE-MANAGER",
                manager_id=USER_IDS["admin"],
                is_active=True,
            ),
        )
        session.add(
            User(
                id=CHARLIE_ID,
                username="charlie",
                password_hash=PASSWORD_HASHES["alice"],
                display_name="Charlie",
                organization_id=DEMO_ORGANIZATION_ID,
                role_id="ROLE-OPERATOR",
                manager_id=OTHER_MANAGER_ID,
                is_active=True,
            ),
        )
        session.add_all(
            [
                UserZoneScope(
                    user_id=OTHER_MANAGER_ID,
                    zone_id=ZONE_C_ID,
                    assigned_by_user_id=USER_IDS["admin"],
                    created_at=datetime(2025, 1, 1, 8, 0),
                ),
                UserZoneScope(
                    user_id=CHARLIE_ID,
                    zone_id=ZONE_C_ID,
                    assigned_by_user_id=OTHER_MANAGER_ID,
                    created_at=datetime(2025, 1, 1, 8, 0),
                ),
            ],
        )

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


def test_manager_lists_only_owned_operators(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "manager", "manager123")

    response = client.get("/api/v1/management/operators", headers=headers)

    assert response.status_code == 200
    assert [operator["username"] for operator in response.json()] == ["alice", "bob"]


def test_manager_can_expand_alice_scope_and_it_takes_effect_immediately(client_and_factory):
    client, _ = client_and_factory
    manager_headers = auth_headers(client, "manager", "manager123")
    alice_headers = auth_headers(client, "alice", "alice123")

    update = client.put(
        f"/api/v1/management/operators/{USER_IDS['alice']}/zones",
        json={"zone_ids": ["ZONE-A", "ZONE-B"]},
        headers=manager_headers,
    )
    after_update = client.get("/api/v1/events/EVT-B01-001", headers=alice_headers)

    assert update.status_code == 200
    assert update.json()["zone_ids"] == ["ZONE-A", "ZONE-B"]
    assert after_update.status_code == 200
    assert after_update.json()["id"] == "EVT-B01-001"


def test_manager_cannot_assign_zone_outside_own_scope(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "manager", "manager123")

    response = client.put(
        f"/api/v1/management/operators/{USER_IDS['alice']}/zones",
        json={"zone_ids": [ZONE_C_ID]},
        headers=headers,
    )

    assert response.status_code == 403


def test_manager_cannot_manage_unowned_operator_admin_or_manager(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "manager", "manager123")

    unowned = client.put(
        f"/api/v1/management/operators/{CHARLIE_ID}/zones",
        json={"zone_ids": [ZONE_C_ID]},
        headers=headers,
    )
    manager_target = client.put(
        f"/api/v1/management/operators/{USER_IDS['manager']}/zones",
        json={"zone_ids": ["ZONE-A"]},
        headers=headers,
    )
    admin_target = client.put(
        f"/api/v1/management/operators/{USER_IDS['admin']}/zones",
        json={"zone_ids": ["ZONE-A"]},
        headers=headers,
    )
    other_manager_target = client.put(
        f"/api/v1/management/operators/{OTHER_MANAGER_ID}/zones",
        json={"zone_ids": [ZONE_C_ID]},
        headers=headers,
    )

    assert unowned.status_code == 403
    assert manager_target.status_code == 403
    assert admin_target.status_code == 403
    assert other_manager_target.status_code == 403


def test_operator_cannot_call_management_api(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "alice", "alice123")

    response = client.get("/api/v1/management/operators", headers=headers)

    assert response.status_code == 403


def test_admin_can_change_manager_scope_without_breaking_delegation(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "admin", "admin123")

    operator_update = client.put(
        f"/api/v1/admin/operators/{USER_IDS['bob']}/zones",
        json={"zone_ids": ["ZONE-A"]},
        headers=headers,
    )
    manager_update = client.put(
        f"/api/v1/admin/managers/{USER_IDS['manager']}/zones",
        json={"zone_ids": ["ZONE-A"]},
        headers=headers,
    )

    assert operator_update.status_code == 200
    assert manager_update.status_code == 200
    assert manager_update.json()["zone_ids"] == ["ZONE-A"]


def test_admin_cannot_assign_operator_scope_outside_current_manager_scope(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "admin", "admin123")

    response = client.put(
        f"/api/v1/admin/operators/{USER_IDS['alice']}/zones",
        json={"zone_ids": [ZONE_C_ID]},
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_assign_operator_to_manager_only_when_scope_is_compatible(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "admin", "admin123")

    incompatible = client.put(
        f"/api/v1/admin/operators/{USER_IDS['alice']}/manager",
        json={"manager_id": OTHER_MANAGER_ID},
        headers=headers,
    )
    compatible = client.put(
        f"/api/v1/admin/operators/{CHARLIE_ID}/manager",
        json={"manager_id": OTHER_MANAGER_ID},
        headers=headers,
    )

    assert incompatible.status_code == 403
    assert compatible.status_code == 200
    assert compatible.json()["manager_id"] == OTHER_MANAGER_ID


def test_admin_routes_are_not_available_to_manager(client_and_factory):
    client, _ = client_and_factory
    headers = auth_headers(client, "manager", "manager123")

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 403
