"""Pydantic schemas for auth API payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserPublic(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    display_name: str | None
    created_at: datetime


class AuthTokenResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserPublic
