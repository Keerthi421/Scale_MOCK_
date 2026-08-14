"""Authentication endpoints."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CurrentEntitlements, CurrentUser, DbSession, auth_rate_limit
from app.schemas.auth import (
    AuthResponse,
    EntitlementsOut,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

RateLimited = Annotated[None, Depends(auth_rate_limit())]


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    # Trust X-Forwarded-For only for its first hop, and only because the app is
    # expected to sit behind a proxy that overwrites it.
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    return user_agent, ip


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: DbSession, _: RateLimited) -> AuthResponse:
    user, tokens = await AuthService(db).signup(
        payload.email, payload.password, payload.display_name
    )
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, db: DbSession, request: Request, _: RateLimited
) -> AuthResponse:
    user_agent, ip = _client_meta(request)
    user, tokens = await AuthService(db).login(
        payload.email, payload.password, user_agent=user_agent, ip_address=ip
    )
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DbSession, request: Request) -> TokenPair:
    user_agent, ip = _client_meta(request)
    _, tokens = await AuthService(db).refresh(
        payload.refresh_token, user_agent=user_agent, ip_address=ip
    )
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DbSession) -> None:
    await AuthService(db).logout(payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: CurrentUser, db: DbSession) -> None:
    await AuthService(db).logout_all(user.id)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/me/entitlements", response_model=EntitlementsOut)
async def my_entitlements(entitlements: CurrentEntitlements) -> EntitlementsOut:
    """Resolved server-side. The client renders from this but never decides it."""
    return EntitlementsOut(**asdict(entitlements))
