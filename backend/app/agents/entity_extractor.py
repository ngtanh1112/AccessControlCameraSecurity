"""Deterministic identifier and video-offset extraction without video analysis."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TypedDict


class EntityResult(TypedDict):
    event_id: str | None
    camera_id: str | None
    zone_id: str | None
    recording_id: str | None
    event_type: str | None
    start_offset_ms: int | None
    end_offset_ms: int | None
    from_time: datetime | None
    to_time: datetime | None


_IDENTIFIER_PATTERNS = {
    "event_id": re.compile(r"\b(EVT-[A-Z0-9-]+)\b", re.IGNORECASE),
    "camera_id": re.compile(r"\b(CAM-[A-Z0-9-]+)\b", re.IGNORECASE),
    "zone_id": re.compile(r"\b(ZONE-[A-Z0-9-]+)\b", re.IGNORECASE),
    "recording_id": re.compile(r"\b(REC-[A-Z0-9-]+)\b", re.IGNORECASE),
}

_MINUTE_RANGE = re.compile(r"từ\s+phút\s+(\d+)\s+đến\s+phút\s+(\d+)", re.IGNORECASE)
_SECOND_RANGE = re.compile(r"từ\s+giây\s+(\d+)\s+đến\s+giây\s+(\d+)", re.IGNORECASE)
_CLOCK_RANGE = re.compile(r"từ\s+(\d{1,2}:\d{2})\s+đến\s+(\d{1,2}:\d{2})", re.IGNORECASE)
_CLOCK_AT = re.compile(r"lúc\s+(\d{1,2}:\d{2})", re.IGNORECASE)


def _empty_entities() -> EntityResult:
    return {
        "event_id": None,
        "camera_id": None,
        "zone_id": None,
        "recording_id": None,
        "event_type": None,
        "start_offset_ms": None,
        "end_offset_ms": None,
        "from_time": None,
        "to_time": None,
    }


def _parse_mmss(value: str) -> int:
    minutes, seconds = (int(part) for part in value.split(":"))
    return (minutes * 60 + seconds) * 1000


def _extract_event_type(message: str) -> str | None:
    text = message.casefold()
    for event_type in ("person_detected", "vehicle_detected", "intrusion_detected"):
        if event_type in text:
            return event_type
    return None


def extract_entities(message: str) -> EntityResult:
    """Extract IDs and normalized video offsets; this never opens or analyzes media."""
    result = _empty_entities()
    for field, pattern in _IDENTIFIER_PATTERNS.items():
        match = pattern.search(message)
        if match is not None:
            result[field] = match.group(1).upper()
    result["event_type"] = _extract_event_type(message)

    minute_match = _MINUTE_RANGE.search(message)
    second_match = _SECOND_RANGE.search(message)
    clock_match = _CLOCK_RANGE.search(message)
    at_match = _CLOCK_AT.search(message)
    if minute_match is not None:
        result["start_offset_ms"] = int(minute_match.group(1)) * 60_000
        result["end_offset_ms"] = int(minute_match.group(2)) * 60_000
    elif second_match is not None:
        result["start_offset_ms"] = int(second_match.group(1)) * 1_000
        result["end_offset_ms"] = int(second_match.group(2)) * 1_000
    elif clock_match is not None:
        result["start_offset_ms"] = _parse_mmss(clock_match.group(1))
        result["end_offset_ms"] = _parse_mmss(clock_match.group(2))
    elif at_match is not None:
        center_offset_ms = _parse_mmss(at_match.group(1))
        result["start_offset_ms"] = max(0, center_offset_ms - 5_000)
        result["end_offset_ms"] = center_offset_ms + 5_000
    return result


class EntityExtractor:
    def extract(self, message: str) -> EntityResult:
        return extract_entities(message)
