from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    ManagerResponse,
    TokenResponse,
    ZoneResponse,
)
from app.security.authn import authenticate_user, create_access_token
from app.security.context import SecurityContext, get_security_context


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(session, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=CurrentUserResponse)
def current_user(
    context: SecurityContext = Depends(get_security_context),
    session: Session = Depends(get_db),
) -> CurrentUserResponse:
    user = session.get(User, context.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    manager = (
        ManagerResponse(id=user.manager.id, username=user.manager.username)
        if user.manager is not None
        else None
    )
    zones = [
        ZoneResponse(id=scope.zone.id, name=scope.zone.name)
        for scope in sorted(user.zone_scopes, key=lambda scope: scope.zone.id)
    ]
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=context.role,
        manager=manager,
        permissions=sorted(context.permissions),
        zones=zones,
    )
