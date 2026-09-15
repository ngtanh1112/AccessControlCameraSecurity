from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.agents.entity_extractor import extract_entities
from app.agents.intent_router import Intent, route_intent
from app.db import Base, create_database_engine
from app.models import AuditLog, ExecutionTrace
from app.security import audit, authorization, execution_trace
from app.security.capability_resolver import resolve_capability
from app.security.context import SecurityContext
from app.security.pre_authorization import PreAuthorizationGate
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
    database_engine = create_database_engine(f"sqlite:///{tmp_path / 'pre-auth-test.db'}")
    Base.metadata.create_all(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    seed_database(factory)
    monkeypatch.setattr(authorization, "SessionLocal", factory)
    monkeypatch.setattr(audit, "SessionLocal", factory)
    monkeypatch.setattr(execution_trace, "SessionLocal", factory)
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


def test_explicit_forbidden_event_is_denied_and_traced_before_agent(seeded_database):
    context = alice_context()
    result = PreAuthorizationGate().evaluate(
        context,
        Intent.VIEW_VIDEO,
        extract_entities("xem video EVT-B01-001"),
    )

    assert result.allowed is False
    assert result.reason == "resource_out_of_scope"
    assert result.action == "media:view_video"
    assert result.resource_type == "media"
    assert result.resource_id == "EVT-B01-001"

    with seeded_database() as session:
        trace = session.scalar(select(ExecutionTrace).where(ExecutionTrace.request_id == context.request_id))
        audit_log = session.scalar(select(AuditLog).where(AuditLog.request_id == context.request_id))
        assert trace is not None
        assert trace.pre_auth_decision == "DENY"
        assert trace.agent_invoked is False
        assert trace.mcp_invoked is False
        assert trace.backend_invoked is False
        assert audit_log is not None
        assert audit_log.decision == "DENY"
        assert audit_log.stage == "PRE_AUTHORIZATION"


def test_explicit_forbidden_camera_time_range_is_denied_without_backend_work(seeded_database):
    context = alice_context()
    message = "CAM-B01 từ 00:40 đến 01:00 có gì"
    intent = route_intent(message)
    entities = extract_entities(message)
    result = PreAuthorizationGate().evaluate(context, intent, entities)

    assert intent == Intent.SEARCH_EVENT
    assert (entities["start_offset_ms"], entities["end_offset_ms"]) == (40_000, 60_000)
    assert result.allowed is False
    assert result.reason == "resource_out_of_scope"

    with seeded_database() as session:
        trace = session.scalar(select(ExecutionTrace).where(ExecutionTrace.request_id == context.request_id))
        assert trace is not None
        assert trace.pre_auth_decision == "DENY"
        assert trace.agent_invoked is False
        assert trace.mcp_invoked is False
        assert trace.backend_invoked is False


def test_missing_permission_is_early_denied_and_audited(seeded_database):
    context = alice_context()
    result = PreAuthorizationGate().evaluate(context, Intent.VIEW_AUDIT, extract_entities("xem audit"))

    assert result.allowed is False
    assert result.reason == "permission_missing"
    assert result.action == "audit:view"

    with seeded_database() as session:
        audit_log = session.scalar(select(AuditLog).where(AuditLog.request_id == context.request_id))
        assert audit_log is not None
        assert audit_log.stage == "PRE_AUTHORIZATION"
        assert audit_log.reason == "permission_missing"


def test_generic_search_allows_only_scoped_camera_ids_and_capability(seeded_database):
    context = alice_context()
    result = PreAuthorizationGate().evaluate(context, Intent.SEARCH_EVENT, extract_entities("tìm event"))

    assert result.allowed is True
    assert result.allowed_camera_ids == ["CAM-A01", "CAM-A02"]
    assert resolve_capability(context, Intent.SEARCH_EVENT) == "search_events"
    assert resolve_capability(context, Intent.VIEW_AUDIT) is None
    with seeded_database() as session:
        trace = session.scalar(select(ExecutionTrace).where(ExecutionTrace.request_id == context.request_id))
        assert trace is not None
        assert trace.pre_auth_decision == "ALLOW"
        assert trace.agent_invoked is False
        assert trace.mcp_invoked is False
        assert trace.backend_invoked is False


def test_unknown_intent_is_denied_with_pre_authorization_audit(seeded_database):
    context = alice_context()
    result = PreAuthorizationGate().evaluate(context, Intent.UNKNOWN, extract_entities("không rõ"))

    assert result.allowed is False
    assert result.reason == "unknown_intent"
    with seeded_database() as session:
        audit_log = session.scalar(select(AuditLog).where(AuditLog.request_id == context.request_id))
        assert audit_log is not None
        assert audit_log.stage == "PRE_AUTHORIZATION"
