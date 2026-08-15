"""AI system-design review.

Owns the whole path from a saved canvas to a stored review: entitlement check,
prompt assembly, structured model call, persistence. Route handlers only
validate input and serialize the result.
"""

from __future__ import annotations

import uuid

from app.ai.base import AIMessage, AIProvider, AIRequest
from app.ai.prompts.system_design import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    DesignSubmission,
    build_review_prompt,
)
from app.core.config import settings
from app.core.entitlements import Entitlements
from app.core.exceptions import PremiumRequiredError, ValidationError
from app.schemas.design_review import DesignReview

# A review is long: many issues, tradeoffs, and per-dimension rationales. This
# ceiling covers thinking plus the JSON body — on Opus 5 thinking is on by
# default and counts against the same budget, so a tight limit truncates the
# JSON mid-object and fails validation rather than erroring cleanly.
_MAX_REVIEW_TOKENS = 16_000

# Guards against a client posting an enormous canvas to burn tokens. Real
# designs in this product are well under these bounds.
_MAX_COMPONENTS = 120
_MAX_CONNECTIONS = 300


class DesignReviewResult:
    __slots__ = ("review", "model_id", "prompt_version", "input_tokens", "output_tokens")

    def __init__(
        self,
        review: DesignReview,
        model_id: str,
        prompt_version: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.review = review
        self.model_id = model_id
        self.prompt_version = prompt_version
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class DesignReviewService:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def review(
        self,
        submission: DesignSubmission,
        *,
        entitlements: Entitlements,
        user_id: uuid.UUID,
    ) -> DesignReviewResult:
        # Authorization first: never spend a model call the user isn't entitled to.
        if not entitlements.allows("can_access_advanced_analytics"):
            raise PremiumRequiredError(
                "AI design review is a premium feature",
                required_tier="premium",
                feature="can_access_advanced_analytics",
            )

        self._validate(submission)

        request = AIRequest(
            system=SYSTEM_PROMPT,
            messages=[AIMessage(role="user", content=build_review_prompt(submission))],
            max_tokens=_MAX_REVIEW_TOKENS,
            effort=settings.ANTHROPIC_EVALUATION_EFFORT,  # type: ignore[arg-type]
            cache_system=True,
            metadata={"user_id": str(user_id), "kind": "design_review"},
        )

        result = await self._provider.generate_structured(request, DesignReview)

        return DesignReviewResult(
            review=result.data,
            model_id=result.model,
            prompt_version=PROMPT_VERSION,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
        )

    @staticmethod
    def _validate(submission: DesignSubmission) -> None:
        if len(submission.components) > _MAX_COMPONENTS:
            raise ValidationError(
                f"Design has too many components (limit {_MAX_COMPONENTS})",
                details={"components": len(submission.components)},
            )
        if len(submission.connections) > _MAX_CONNECTIONS:
            raise ValidationError(
                f"Design has too many connections (limit {_MAX_CONNECTIONS})",
                details={"connections": len(submission.connections)},
            )
