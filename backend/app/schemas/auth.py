from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ManagerResponse(BaseModel):
    id: str
    username: str


class ZoneResponse(BaseModel):
    id: str
    name: str


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    manager: ManagerResponse | None
    permissions: list[str]
    zones: list[ZoneResponse]
