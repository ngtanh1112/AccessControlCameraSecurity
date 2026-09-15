from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")
    role: Mapped["Role"] = relationship(back_populates="users")
    manager: Mapped["User | None"] = relationship(
        back_populates="operators",
        remote_side="User.id",
    )
    operators: Mapped[list["User"]] = relationship(back_populates="manager")
    zone_scopes: Mapped[list["UserZoneScope"]] = relationship(
        back_populates="user",
        foreign_keys="UserZoneScope.user_id",
        cascade="all, delete-orphan",
    )


class UserZoneScope(Base):
    __tablename__ = "user_zone_scopes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), primary_key=True)
    assigned_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(
        back_populates="zone_scopes",
        foreign_keys=[user_id],
    )
    zone: Mapped["Zone"] = relationship(back_populates="user_scopes")
