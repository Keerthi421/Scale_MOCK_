"""Request/response models for authentication."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import SubscriptionTier, UserRole

# Reject passwords that are long but trivially weak. Deliberately not a
# maximalist policy — length carries most of the strength, and over-strict
# rules push users toward predictable substitutions.
_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not _HAS_LETTER.search(v) or not _HAS_DIGIT.search(v):
            raise ValueError("password must contain at least one letter and one digit")
        return v

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("display_name cannot be blank")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access_token expires


class EntitlementsOut(BaseModel):
    tier: SubscriptionTier
    max_problems: int
    interviews_per_week: int
    can_access_premium_problems: bool
    can_access_full_study_guides: bool
    can_access_advanced_analytics: bool
    can_access_company_guides: bool
    can_request_resume_review: bool
    can_access_mentoring: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    bio: str | None
    role: UserRole
    subscription_tier: SubscriptionTier
    email_verified_at: datetime | None
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not _HAS_LETTER.search(v) or not _HAS_DIGIT.search(v):
            raise ValueError("password must contain at least one letter and one digit")
        return v
