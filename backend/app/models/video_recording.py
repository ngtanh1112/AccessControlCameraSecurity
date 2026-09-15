from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VideoAnalysisStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoRecording(Base):
    __tablename__ = "video_recordings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    recording_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_status: Mapped[VideoAnalysisStatus] = mapped_column(
        SqlEnum(VideoAnalysisStatus),
        nullable=False,
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    camera: Mapped["Camera"] = relationship(back_populates="video_recordings")
    events: Mapped[list["Event"]] = relationship(back_populates="recording")
