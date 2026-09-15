"""Reusable SecurityContext constructed from current database state."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security.authn import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class SecurityContext:
    request_id: str
    user_id: str
    username: str
    organization_id: str
    role: str
    permissions: set[str]
    allowed_zone_ids: set[str]


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_security_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> SecurityContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_exception()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = str(payload["sub"])
    except (KeyError, ValueError):
        raise _credentials_exception() from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()

    if payload["username"] != user.username or payload["org_id"] != user.organization_id:
        raise _credentials_exception()

    return SecurityContext(
        request_id=str(uuid4()),
        user_id=user.id,
        username=user.username,
        organization_id=user.organization_id,
        role=user.role.name.value,
        permissions={permission.code for permission in user.role.permissions},
        allowed_zone_ids={scope.zone_id for scope in user.zone_scopes},
    )
