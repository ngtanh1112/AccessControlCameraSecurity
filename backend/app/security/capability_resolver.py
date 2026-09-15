"""Resolve only capabilities whose backing permission is currently granted."""

from __future__ import annotations

from app.agents.intent_router import Intent
from app.security.context import SecurityContext


INTENT_ACTIONS: dict[Intent, str] = {
    Intent.LIST_MY_CAMERAS: "camera:list",
    Intent.SEARCH_EVENT: "event:search",
    Intent.VIEW_EVENT: "event:view",
    Intent.VIEW_IMAGE: "media:view_image",
    Intent.VIEW_VIDEO: "media:view_video",
    Intent.VIEW_LIVE_CAMERA: "camera:view_live",
    Intent.CREATE_ALERT: "alert:create",
    Intent.SEARCH_SYSTEM_LOG: "system_log:view",
    Intent.VIEW_AUDIT: "audit:view",
}

INTENT_CAPABILITIES: dict[Intent, str] = {
    Intent.LIST_MY_CAMERAS: "list_cameras",
    Intent.SEARCH_EVENT: "search_events",
    Intent.VIEW_EVENT: "get_event",
    Intent.VIEW_IMAGE: "get_event_image",
    Intent.VIEW_VIDEO: "get_event_video",
    Intent.VIEW_LIVE_CAMERA: "get_camera_live",
    Intent.CREATE_ALERT: "create_alert",
    Intent.SEARCH_SYSTEM_LOG: "search_system_logs",
    Intent.VIEW_AUDIT: "get_audit_logs",
}


def action_for_intent(intent: Intent) -> str | None:
    return INTENT_ACTIONS.get(intent)


def resolve_capability(context: SecurityContext, intent: Intent) -> str | None:
    action = action_for_intent(intent)
    if action is None or action not in context.permissions:
        return None
    return INTENT_CAPABILITIES.get(intent)
