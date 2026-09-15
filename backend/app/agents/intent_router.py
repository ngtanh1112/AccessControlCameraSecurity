"""Small deterministic intent router with no external LLM dependency."""

from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    LIST_MY_CAMERAS = "LIST_MY_CAMERAS"
    SEARCH_EVENT = "SEARCH_EVENT"
    VIEW_EVENT = "VIEW_EVENT"
    VIEW_IMAGE = "VIEW_IMAGE"
    VIEW_VIDEO = "VIEW_VIDEO"
    VIEW_LIVE_CAMERA = "VIEW_LIVE_CAMERA"
    CREATE_ALERT = "CREATE_ALERT"
    SEARCH_SYSTEM_LOG = "SEARCH_SYSTEM_LOG"
    VIEW_AUDIT = "VIEW_AUDIT"
    UNKNOWN = "UNKNOWN"


def route_intent(message: str) -> Intent:
    text = message.casefold()

    if "xem audit" in text:
        return Intent.VIEW_AUDIT
    if "xem log" in text:
        return Intent.SEARCH_SYSTEM_LOG
    if "tạo cảnh báo" in text or "tao canh bao" in text:
        return Intent.CREATE_ALERT
    if "xem live" in text or "live cam" in text:
        return Intent.VIEW_LIVE_CAMERA
    if "xem ảnh" in text or "xem anh" in text:
        return Intent.VIEW_IMAGE
    if "xem video" in text:
        return Intent.VIEW_VIDEO
    if "camera nào tôi được xem" in text or "camera nao toi duoc xem" in text:
        return Intent.LIST_MY_CAMERAS
    if "tìm event" in text or "tim event" in text or "tìm sự kiện" in text or "tim su kien" in text:
        return Intent.SEARCH_EVENT
    if "có gì" in text or "co gi" in text:
        return Intent.SEARCH_EVENT
    if "xem evt-" in text or "xem sự kiện" in text or "xem su kien" in text:
        return Intent.VIEW_EVENT
    return Intent.UNKNOWN


class IntentRouter:
    def route(self, message: str) -> Intent:
        return route_intent(message)
