from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.db import Base, create_database_engine
from app.mcp.tools import system_log
from app.mcp.tools.alert import CreateAlertTool
from app.mcp.tools.system_log import SearchSystemLogsTool
from app.models import SystemLog
from app.security import audit, authorization
from app.security.context import SecurityContext
from app.security.gateway import AccessDenied
from app.seed import DEMO_ORGANIZATION_ID, USER_IDS, seed_database
from app.services.notification_service import NotificationService


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'alert-system-log-test.db'}")
    Base.metadata.create_all(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(factory)
    monkeypatch.setattr(authorization, "SessionLocal", factory)
    monkeypatch.setattr(audit, "SessionLocal", factory)
    monkeypatch.setattr(system_log, "SessionLocal", factory)
    yield factory
    database_engine.dispose()


def zone_a_manager_context() -> SecurityContext:
    return SecurityContext(
        request_id=str(uuid4()),
        user_id=USER_IDS["manager"],
        username="manager",
        organization_id=DEMO_ORGANIZATION_ID,
        role="MANAGER",
        permissions={"system_log:view"},
        allowed_zone_ids={"ZONE-A"},
    )


def alice_context() -> SecurityContext:
    return SecurityContext(
        request_id=str(uuid4()),
        user_id=USER_IDS["alice"],
        username="alice",
        organization_id=DEMO_ORGANIZATION_ID,
        role="OPERATOR",
        permissions={"alert:create"},
        allowed_zone_ids={"ZONE-A"},
    )


def test_alice_alert_is_allowed_only_for_camera_in_her_scope(seeded_database):
    notifications = NotificationService()
    tool = CreateAlertTool(notifications)

    created = tool.execute(alice_context(), {"camera_id": "CAM-A01", "message": "Check entrance"})

    assert created["camera_id"] == "CAM-A01"
    assert created["message"] == "Check entrance"
    assert created["created_by"] == USER_IDS["alice"]
    assert len(notifications.list_notifications()) == 1

    with pytest.raises(AccessDenied) as error:
        tool.execute(alice_context(), {"camera_id": "CAM-B01"})

    assert error.value.decision.reason == "resource_out_of_scope"
    assert [item["camera_id"] for item in notifications.list_notifications()] == ["CAM-A01"]


def test_system_log_search_returns_only_allowed_camera_logs(seeded_database):
    with seeded_database.begin() as session:
        session.add_all(
            [
                SystemLog(
                    id="LOG-GLOBAL",
                    source="system",
                    level="INFO",
                    message="Global service started",
                    camera_id=None,
                    created_at=datetime(2025, 1, 1, 8, 0),
                ),
                SystemLog(
                    id="LOG-A01",
                    source="camera",
                    level="INFO",
                    message="Zone A camera online",
                    camera_id="CAM-A01",
                    created_at=datetime(2025, 1, 1, 8, 1),
                ),
                SystemLog(
                    id="LOG-B01",
                    source="camera",
                    level="WARN",
                    message="Zone B camera offline",
                    camera_id="CAM-B01",
                    created_at=datetime(2025, 1, 1, 8, 2),
                ),
            ],
        )

    tool = SearchSystemLogsTool()
    manager = zone_a_manager_context()

    logs = tool.execute(manager, {})

    assert [log["id"] for log in logs] == ["LOG-GLOBAL", "LOG-A01"]
    with pytest.raises(AccessDenied) as error:
        tool.execute(manager, {"camera_id": "CAM-B01"})
    assert error.value.decision.reason == "resource_out_of_scope"
