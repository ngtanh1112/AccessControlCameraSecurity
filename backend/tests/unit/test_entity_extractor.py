from app.agents.entity_extractor import extract_entities
from app.agents.intent_router import Intent, route_intent


def test_routes_required_deterministic_examples():
    assert route_intent("camera nào tôi được xem") == Intent.LIST_MY_CAMERAS
    assert route_intent("tìm sự kiện") == Intent.SEARCH_EVENT
    assert route_intent("CAM-A01 từ 00:40 đến 01:00 có gì") == Intent.SEARCH_EVENT
    assert route_intent("xem EVT-A01-001") == Intent.VIEW_EVENT
    assert route_intent("xem ảnh EVT-A01-001") == Intent.VIEW_IMAGE
    assert route_intent("xem video EVT-A01-001") == Intent.VIEW_VIDEO
    assert route_intent("xem live CAM-A01") == Intent.VIEW_LIVE_CAMERA
    assert route_intent("tạo cảnh báo") == Intent.CREATE_ALERT
    assert route_intent("xem log") == Intent.SEARCH_SYSTEM_LOG
    assert route_intent("xem audit") == Intent.VIEW_AUDIT


def test_extracts_identifiers_and_clock_range_as_video_offsets():
    entities = extract_entities("CAM-B01 từ 00:40 đến 01:00 có gì với EVT-B01-001?")

    assert entities["camera_id"] == "CAM-B01"
    assert entities["event_id"] == "EVT-B01-001"
    assert entities["start_offset_ms"] == 40_000
    assert entities["end_offset_ms"] == 60_000
    assert entities["from_time"] is None
    assert entities["to_time"] is None


def test_extracts_minute_and_second_ranges_as_milliseconds():
    minute_entities = extract_entities("CAM-A01 từ phút 1 đến phút 2 có gì")
    second_entities = extract_entities("CAM-A01 từ giây 40 đến giây 60 có gì")

    assert (minute_entities["start_offset_ms"], minute_entities["end_offset_ms"]) == (60_000, 120_000)
    assert (second_entities["start_offset_ms"], second_entities["end_offset_ms"]) == (40_000, 60_000)


def test_extracts_single_timestamp_with_small_query_window():
    entities = extract_entities("CAM-A01 lúc 00:46 có gì")

    assert (entities["start_offset_ms"], entities["end_offset_ms"]) == (41_000, 51_000)
