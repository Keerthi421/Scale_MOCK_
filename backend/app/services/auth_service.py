"""Authentication business logic.

Route handlers stay thin; everything that decides *whether* a login succeeds
lives here so it can be unit-tested without HTTP.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from app.models.enums import SubscriptionStatus, SubscriptionTier
from app.models.progress import UserProgress
from app.models.user import RefreshToken, Subscription, User
from app.schemas.auth import TokenPair


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Registration ------------------------------------------------------

    async def signup(self, email: str, password: str, display_name: str) -> tuple[User, TokenPair]:
        normalized = email.strip().lower()

        existing = await self.db.scalar(select(User).where(User.email == normalized))
        if existing is not None:
            raise ConflictError("An account with this email already exists")

        user = User(
            email=normalized,
            password_hash=hash_password(password),
            display_name=display_name,
            subscription_tier=SubscriptionTier.FREE,
        )
        # Created eagerly so no downstream code has to handle "user exists but
        # has no subscription/progress row yet".
        user.subscription = Subscription(
            tier=SubscriptionTier.FREE, status=SubscriptionStatus.ACTIVE
        )
        user.progress = UserProgress()

        self.db.add(user)
        await self.db.flush()

        tokens = await self._issue_token_pair(user)
        return user, tokens

    # --- Login -------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair]:
        normalized = email.strip().lower()
        user = await self.db.scalar(select(User).where(User.email == normalized))

        # Identical error and comparable timing whether the account is missing,
        # OAuth-only, or the password is wrong — otherwise this endpoint becomes
        # an account-enumeration oracle.
        if user is None or user.password_hash is None:
            hash_password(password)  # burn equivalent CPU
            raise AuthenticationError("Incorrect email or password")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Incorrect email or password")

        if not user.is_active:
            raise AuthenticationError("This account has been disabled")

        # Transparently upgrade the hash if Argon2 parameters have changed.
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        user.last_login_at = datetime.now(UTC)
        tokens = await self._issue_token_pair(user, user_agent=user_agent, ip_address=ip_address)
        return user, tokens

    # --- Refresh -----------------------------------------------------------

    async def refresh(
        self,
        raw_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair]:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

        if stored is None:
            raise AuthenticationError("Invalid refresh token")

        now = datetime.now(UTC)

        if stored.revoked_at is not None:
            # A revoked token being presented again means it was captured and
            # replayed. The legitimate holder's successor token is also
            # compromised, so the entire rotation family is burned.
            await self._revoke_family(stored.family_id)
            raise AuthenticationError("Refresh token reuse detected; all sessions revoked")

        if stored.expires_at < now:
            raise AuthenticationError("Refresh token expired")

        user = await self.db.get(User, stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account unavailable")

        stored.revoked_at = now
        tokens = await self._issue_token_pair(
            user,
            family_id=stored.family_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return user, tokens

    # --- Logout ------------------------------------------------------------

    async def logout(self, raw_token: str) -> None:
        """Revoke the presented token's whole family (this device's session)."""
        token_hash = hash_refresh_token(raw_token)
        stored = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        # Silent success on an unknown token: logout must be idempotent and must
        # not reveal whether a token was valid.
        if stored is not None:
            await self._revoke_family(stored.family_id)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    # --- Internals ---------------------------------------------------------

    async def _issue_token_pair(
        self,
        user: User,
        *,
        family_id: uuid.UUID | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        raw_refresh, refresh_hash = generate_refresh_token()

        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
                family_id=family_id or uuid.uuid4(),
                user_agent=(user_agent or "")[:400] or None,
                ip_address=ip_address,
            )
        )

        # Role is embedded so authorization for the common case needs no DB
        # read. Entitlements are deliberately NOT embedded — they change on
        # payment events and must always be read fresh.
        access = create_access_token(user.id, extra_claims={"role": user.role.value})

        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
        )

    async def _revoke_family(self, family_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
