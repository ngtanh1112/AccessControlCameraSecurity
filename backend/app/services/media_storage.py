"""Private local media storage; files are served only through protected APIs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


class MediaStorage:
    def __init__(self, media_root: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        configured = Path(os.getenv("MEDIA_ROOT", "data"))
        self.project_root = project_root
        self.media_root = media_root or (configured if configured.is_absolute() else project_root / configured)
        self.videos_dir = self.media_root / "videos"
        self.snapshots_dir = self.media_root / "snapshots"
        self.clips_dir = self.media_root / "clips"
        for directory in (self.videos_dir, self.snapshots_dir, self.clips_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _relative(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.project_root).as_posix()
        except ValueError:
            # Test media roots can deliberately live outside the repository.
            return str(resolved)

    def resolve(self, stored_path: str | None) -> Path | None:
        if stored_path is None:
            return None
        path = Path(stored_path)
        return path if path.is_absolute() else self.project_root / path

    def save_upload(self, recording_id: str, source: Path) -> str:
        target = self.videos_dir / f"{recording_id}.mp4"
        shutil.copyfile(source, target)
        return self._relative(target)

    def save_snapshot(self, event_id: str, frame: Any | None) -> str | None:
        if frame is None:
            return None
        try:
            import cv2  # type: ignore[import-not-found]

            target = self.snapshots_dir / f"{event_id}.jpg"
            if not cv2.imwrite(str(target), frame):
                return None
            return self._relative(target)
        except Exception:
            return None

    def create_clip(
        self,
        *,
        event_id: str,
        recording_path: str,
        start_offset_ms: int,
        end_offset_ms: int,
        duration_ms: int | None,
        padding_seconds: float,
    ) -> str | None:
        try:
            import cv2  # type: ignore[import-not-found]

            source = self.resolve(recording_path)
            if source is None or not source.is_file():
                return None
            capture = cv2.VideoCapture(str(source))
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if not capture.isOpened() or fps <= 0 or width <= 0 or height <= 0:
                capture.release()
                return None
            start_ms = max(0, start_offset_ms - int(padding_seconds * 1000))
            end_ms = end_offset_ms + int(padding_seconds * 1000)
            if duration_ms is not None:
                end_ms = min(end_ms, duration_ms)
            target = self.clips_dir / f"{event_id}.mp4"
            writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
            if not writer.isOpened():
                capture.release()
                return None
            capture.set(cv2.CAP_PROP_POS_MSEC, start_ms)
            try:
                while capture.get(cv2.CAP_PROP_POS_MSEC) <= end_ms:
                    ok, frame = capture.read()
                    if not ok:
                        break
                    writer.write(frame)
            finally:
                writer.release()
                capture.release()
            return self._relative(target) if target.is_file() else None
        except Exception:
            return None
