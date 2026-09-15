from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), nullable=False)
    status: Mapped[CameraStatus] = mapped_column(SqlEnum(CameraStatus), nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="cameras")
    zone: Mapped["Zone"] = relationship(back_populates="cameras")
    events: Mapped[list["Event"]] = relationship(back_populates="camera")
    video_recordings: Mapped[list["VideoRecording"]] = relationship(back_populates="camera")
    system_logs: Mapped[list["SystemLog"]] = relationship(back_populates="camera")
