"""Application error types.

Services raise these; a single exception handler in main.py turns them into
responses. Route handlers never construct HTTPException directly, so error
shape stays consistent across the API.
"""

from typing import Any


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class PremiumRequiredError(AppError):
    """Distinct from PermissionDenied so the client can show an upgrade path
    rather than a generic 'forbidden'."""

    status_code = 402
    code = "premium_required"

    def __init__(self, message: str, *, required_tier: str, feature: str) -> None:
        super().__init__(message, details={"required_tier": required_tier, "feature": feature})


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message, details={"retry_after_seconds": retry_after_seconds})
        self.retry_after_seconds = retry_after_seconds


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
