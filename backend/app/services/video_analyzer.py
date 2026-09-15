"""Pretrained YOLO and deterministic fake video analysis implementations."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models import VideoRecording


SUPPORTED_CLASS_TO_EVENT = {
    "person": "person_detected",
    "car": "vehicle_detected",
    "motorcycle": "vehicle_detected",
    "bus": "vehicle_detected",
    "truck": "vehicle_detected",
}


@dataclass(frozen=True)
class Detection:
    timestamp_ms: int
    event_type: str
    confidence: float
    frame: Any | None = None


@dataclass(frozen=True)
class DetectedEvent:
    event_type: str
    start_offset_ms: int
    end_offset_ms: int
    confidence: float
    best_frame: Any | None = None


class VideoAnalyzer(ABC):
    @abstractmethod
    def analyze(self, recording: VideoRecording) -> list[DetectedEvent]:
        """Return time-range events without persisting them."""


def aggregate_detections(
    detections: list[Detection],
    *,
    merge_gap_seconds: float,
    minimum_duration_seconds: float,
) -> list[DetectedEvent]:
    """Merge same-type nearby detections into deterministic time-range events."""
    del minimum_duration_seconds  # One meaningful sampled detection remains an event in this POC.
    max_gap_ms = int(merge_gap_seconds * 1000)
    aggregates: list[DetectedEvent] = []
    for event_type in sorted({item.event_type for item in detections}):
        items = sorted((item for item in detections if item.event_type == event_type), key=lambda item: item.timestamp_ms)
        if not items:
            continue
        start = end = items[0].timestamp_ms
        best = items[0]
        previous = items[0]
        for item in items[1:]:
            if item.timestamp_ms - previous.timestamp_ms <= max_gap_ms:
                end = item.timestamp_ms
                if item.confidence > best.confidence:
                    best = item
            else:
                aggregates.append(DetectedEvent(event_type, start, end, best.confidence, best.frame))
                start = end = item.timestamp_ms
                best = item
            previous = item
        aggregates.append(DetectedEvent(event_type, start, end, best.confidence, best.frame))
    return sorted(aggregates, key=lambda item: (item.start_offset_ms, item.event_type))


class YoloVideoAnalyzer(VideoAnalyzer):
    """Analyze a local MP4 with pretrained Ultralytics YOLO; never trains a model."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        sample_fps: float | None = None,
        merge_gap_seconds: float | None = None,
        minimum_duration_seconds: float | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("YOLO_MODEL", "yolo11n.pt")
        self.sample_fps = sample_fps if sample_fps is not None else float(os.getenv("VIDEO_SAMPLE_FPS", "5"))
        self.merge_gap_seconds = merge_gap_seconds if merge_gap_seconds is not None else float(os.getenv("EVENT_MERGE_GAP_SECONDS", "2.0"))
        self.minimum_duration_seconds = minimum_duration_seconds if minimum_duration_seconds is not None else float(os.getenv("EVENT_MIN_DURATION_SECONDS", "0.5"))
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.40"))

    def analyze(self, recording: VideoRecording) -> list[DetectedEvent]:
        # Imports are intentionally lazy: automated tests use FakeVideoAnalyzer and never load YOLO weights.
        import cv2  # type: ignore[import-not-found]
        from ultralytics import YOLO  # type: ignore[import-not-found]

        stored_path = Path(recording.stored_path)
        source_path = stored_path if stored_path.is_absolute() else Path(__file__).resolve().parents[3] / stored_path
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video recording: {recording.stored_path}")
        try:
            source_fps = float(capture.get(cv2.CAP_PROP_FPS))
            if source_fps <= 0 or not source_fps == source_fps:
                source_fps = max(self.sample_fps, 1.0)
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            recording.duration_ms = int((frame_count / source_fps) * 1000) if frame_count > 0 else None
            stride = max(1, round(source_fps / max(self.sample_fps, 0.1)))
            model = YOLO(self.model_name)
            detections: list[Detection] = []
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % stride == 0:
                    timestamp_ms = int((frame_index / source_fps) * 1000)
                    result = model(frame, verbose=False, conf=self.confidence_threshold)[0]
                    per_type: dict[str, tuple[float, Any]] = {}
                    names = result.names
                    for box in result.boxes:
                        class_name = str(names[int(box.cls[0])])
                        event_type = SUPPORTED_CLASS_TO_EVENT.get(class_name)
                        confidence = float(box.conf[0])
                        if event_type is not None and confidence >= self.confidence_threshold:
                            previous = per_type.get(event_type)
                            if previous is None or confidence > previous[0]:
                                per_type[event_type] = (confidence, frame.copy())
                    detections.extend(
                        Detection(timestamp_ms, event_type, confidence, best_frame)
                        for event_type, (confidence, best_frame) in per_type.items()
                    )
                frame_index += 1
            return aggregate_detections(
                detections,
                merge_gap_seconds=self.merge_gap_seconds,
                minimum_duration_seconds=self.minimum_duration_seconds,
            )
        finally:
            capture.release()


class FakeVideoAnalyzer(VideoAnalyzer):
    """Deterministic no-download analyzer for tests, CI, and local fallback debugging."""

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, recording: VideoRecording) -> list[DetectedEvent]:
        self.calls += 1
        recording.duration_ms = 45_000
        # Numpy frames make snapshot persistence testable without importing YOLO.
        import numpy as np

        return [
            DetectedEvent("person_detected", 10_000, 15_000, 0.91, np.full((32, 48, 3), 80, dtype=np.uint8)),
            DetectedEvent("vehicle_detected", 40_000, 45_000, 0.87, np.full((32, 48, 3), 160, dtype=np.uint8)),
        ]


def create_video_analyzer() -> VideoAnalyzer:
    if os.getenv("VIDEO_ANALYZER_MODE", "yolo").casefold() == "fake":
        return FakeVideoAnalyzer()
    return YoloVideoAnalyzer()
