"""JWT authentication helpers; authorization is intentionally out of scope here."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


DEFAULT_JWT_SECRET = "dev-secret-change-me"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_EXPIRE_MINUTES = 120


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)


def _jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", DEFAULT_JWT_ALGORITHM)


def _jwt_expire_minutes() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", str(DEFAULT_JWT_EXPIRE_MINUTES)))


def verify_password(password: str, password_hash: str) -> bool:
    return pbkdf2_sha256.verify(password, password_hash)


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_jwt_expire_minutes())
    payload = {
        "sub": user.id,
        "username": user.username,
        "org_id": user.organization_id,
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
    except JWTError as error:
        raise ValueError("Invalid access token") from error

    if not all(payload.get(key) for key in ("sub", "username", "org_id")):
        raise ValueError("Invalid access token")
    return payload
