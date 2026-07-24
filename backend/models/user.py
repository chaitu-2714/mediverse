"""
Pydantic Request/Response schemas for user authentication.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = "medical_student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class OnboardingRequest(BaseModel):
    role: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class SSOExchangeRequest(BaseModel):
    provider: str
    uid: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    firebase_id_token: Optional[str] = None
