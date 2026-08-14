"""Single source of truth for what a tier may do.

Every premium check in the codebase resolves through `get_entitlements`. No
route, service, or client is permitted to decide access on its own — that is
what keeps "is this user premium?" from drifting into a dozen slightly
different answers, and what stops the frontend from being part of the security
boundary.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.enums import SubscriptionStatus, SubscriptionTier
from app.models.user import User

# Sentinel for "no cap". Chosen over None so callers can compare numerically
# without a null check on every limit.
UNLIMITED = -1


@dataclass(frozen=True, slots=True)
class Entitlements:
    tier: SubscriptionTier
    max_problems: int
    interviews_per_week: int
    can_access_premium_problems: bool
    can_access_full_study_guides: bool
    can_access_advanced_analytics: bool
    can_access_company_guides: bool
    can_request_resume_review: bool
    can_access_mentoring: bool

    def allows(self, feature: str) -> bool:
        return bool(getattr(self, feature, False))


_FREE = Entitlements(
    tier=SubscriptionTier.FREE,
    max_problems=10,
    interviews_per_week=2,
    can_access_premium_problems=False,
    can_access_full_study_guides=False,
    can_access_advanced_analytics=False,
    can_access_company_guides=False,
    can_request_resume_review=False,
    can_access_mentoring=False,
)

_PREMIUM = Entitlements(
    tier=SubscriptionTier.PREMIUM,
    max_problems=UNLIMITED,
    interviews_per_week=UNLIMITED,
    can_access_premium_problems=True,
    can_access_full_study_guides=True,
    can_access_advanced_analytics=True,
    can_access_company_guides=False,
    can_request_resume_review=False,
    can_access_mentoring=False,
)

_PRO = Entitlements(
    tier=SubscriptionTier.PRO,
    max_problems=UNLIMITED,
    interviews_per_week=UNLIMITED,
    can_access_premium_problems=True,
    can_access_full_study_guides=True,
    can_access_advanced_analytics=True,
    can_access_company_guides=True,
    can_request_resume_review=True,
    can_access_mentoring=True,
)

_BY_TIER: dict[SubscriptionTier, Entitlements] = {
    SubscriptionTier.FREE: _FREE,
    SubscriptionTier.PREMIUM: _PREMIUM,
    SubscriptionTier.PRO: _PRO,
}


def get_entitlements(user: User) -> Entitlements:
    """Resolve effective entitlements from authoritative subscription state.

    Deliberately reads `user.subscription` rather than the denormalized
    `user.subscription_tier`, and independently re-checks expiry: a lapsed
    subscription that a webhook failed to downgrade must still degrade to free
    rather than granting access until someone notices.
    """
    sub = user.subscription
    if sub is None:
        return _FREE

    if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        return _FREE

    if sub.current_period_end is not None and sub.current_period_end < datetime.now(UTC):
        return _FREE

    return _BY_TIER.get(sub.tier, _FREE)
