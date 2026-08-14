"""Shared FastAPI dependencies: current user, RBAC, entitlements, rate limits."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.entitlements import Entitlements, get_entitlements
from app.core.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    PremiumRequiredError,
    RateLimitError,
)
from app.core.redis import check_rate_limit
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

# auto_error=False so a missing header raises our AuthenticationError with the
# standard error envelope rather than FastAPI's default 403 shape.
_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication required")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid access token") from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Malformed access token") from exc

    # Subscription is eager-loaded because get_entitlements needs it and this is
    # the hot path for every authenticated request.
    user = await db.scalar(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )

    if user is None or not user.is_active:
        raise AuthenticationError("Account unavailable")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """For endpoints that show more to signed-in users but allow anonymous access."""
    if credentials is None:
        return None
    try:
        return await get_current_user(db, credentials)
    except AuthenticationError:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Administrator access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def current_entitlements(user: CurrentUser) -> Entitlements:
    return get_entitlements(user)


CurrentEntitlements = Annotated[Entitlements, Depends(current_entitlements)]


def require_feature(feature: str, *, required_tier: str = "premium") -> Callable[..., Entitlements]:
    """Dependency factory gating a route behind one entitlement flag.

    Usage:
        @router.get("/x", dependencies=[Depends(require_feature("can_access_premium_problems"))])
    """

    def _dependency(entitlements: CurrentEntitlements) -> Entitlements:
        if not entitlements.allows(feature):
            raise PremiumRequiredError(
                "This feature requires an upgraded plan",
                required_tier=required_tier,
                feature=feature,
            )
        return entitlements

    return _dependency


def rate_limit(
    limit: int, window_seconds: int, *, scope: str
) -> Callable[..., object]:
    """Per-user (or per-IP when anonymous) sliding-window limiter."""

    async def _dependency(request: Request, user: OptionalUser) -> None:
        identity = str(user.id) if user else (request.client.host if request.client else "unknown")
        allowed, retry_after = await check_rate_limit(
            f"{scope}:{identity}", limit, window_seconds
        )
        if not allowed:
            raise RateLimitError(
                "Too many requests; please slow down", retry_after_seconds=retry_after
            )

    return _dependency


def auth_rate_limit() -> Callable[..., object]:
    limit, window = settings.RATE_LIMIT_AUTH
    return rate_limit(limit, window, scope="auth")


def ai_rate_limit() -> Callable[..., object]:
    limit, window = settings.RATE_LIMIT_AI
    return rate_limit(limit, window, scope="ai")
