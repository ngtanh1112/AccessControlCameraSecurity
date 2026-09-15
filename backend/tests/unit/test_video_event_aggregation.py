from __future__ import annotations

from app.services.video_analyzer import Detection, aggregate_detections


def test_aggregation_merges_nearby_detections_without_frame_spam():
    events = aggregate_detections(
        [
            Detection(1_000, "person_detected", 0.70),
            Detection(1_500, "person_detected", 0.92),
            Detection(2_000, "person_detected", 0.80),
            Detection(5_500, "person_detected", 0.88),
        ],
        merge_gap_seconds=2.0,
        minimum_duration_seconds=0.5,
    )

    assert [(event.start_offset_ms, event.end_offset_ms, event.confidence) for event in events] == [
        (1_000, 2_000, 0.92),
        (5_500, 5_500, 0.88),
    ]


def test_aggregation_keeps_person_and_vehicle_as_distinct_time_ranges():
    events = aggregate_detections(
        [
            Detection(1_000, "person_detected", 0.90),
            Detection(1_500, "vehicle_detected", 0.85),
            Detection(2_000, "person_detected", 0.91),
        ],
        merge_gap_seconds=2.0,
        minimum_duration_seconds=0.5,
    )

    assert [(event.event_type, event.start_offset_ms, event.end_offset_ms) for event in events] == [
        ("person_detected", 1_000, 2_000),
        ("vehicle_detected", 1_500, 1_500),
    ]
