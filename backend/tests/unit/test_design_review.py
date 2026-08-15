"""Design review: authorization, schema sanitization, and input bounds."""

from __future__ import annotations

import json
import uuid

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.ai.anthropic_provider import _sanitize_schema
from app.ai.base import AIRequest, AIStructuredResponse, AIUsage
from app.ai.prompts.system_design import DesignSubmission, build_review_prompt
from app.core.entitlements import _FREE, _PREMIUM
from app.core.exceptions import PremiumRequiredError, ValidationError
from app.schemas.design_review import DesignReview, DimensionScore
from app.services.design_review_service import DesignReviewService

_REVIEW = DesignReview(
    overall_score=71.0,
    summary_md="Solid baseline.\n\nMisses replication.",
    dimension_scores=[
        DimensionScore(dimension="caching", score=80.0, rationale="Redis read-through.")
    ],
    issues=[],
    tradeoffs=[],
    capacity_checks=[],
    missing_components=["read replica"],
    bottlenecks=["single primary"],
    single_points_of_failure=["primary database"],
    strengths=["clear request path"],
    next_steps=["Add a read replica."],
)


class FakeProvider:
    """Records the request instead of calling the network."""

    def __init__(self) -> None:
        self.last_request: AIRequest | None = None
        self.calls = 0

    @property
    def model_id(self) -> str:
        return "fake-model"

    async def generate(self, request: AIRequest):  # pragma: no cover - unused here
        raise NotImplementedError

    def stream(self, request: AIRequest):  # pragma: no cover - unused here
        raise NotImplementedError

    async def generate_structured(self, request: AIRequest, schema: type[BaseModel]):
        self.calls += 1
        self.last_request = request
        return AIStructuredResponse(
            data=_REVIEW,
            usage=AIUsage(input_tokens=1200, output_tokens=900),
            model="fake-model",
        )


def _submission(**overrides: object) -> DesignSubmission:
    base = {
        "problem_title": "Design a URL Shortener",
        "problem_statement": "Map long URLs to short codes.",
        "functional_requirements": ["Create link", "Redirect"],
        "non_functional_requirements": ["100M writes/day"],
        "components": ["Client", "API Gateway", "Postgres"],
        "connections": ["Client -> API Gateway"],
    }
    base.update(overrides)
    return DesignSubmission(**base)  # type: ignore[arg-type]


async def test_free_tier_is_rejected_before_any_model_call() -> None:
    """The gate must run first — a refused user must not cost a model call."""
    provider = FakeProvider()
    service = DesignReviewService(provider)

    with pytest.raises(PremiumRequiredError) as exc:
        await service.review(_submission(), entitlements=_FREE, user_id=uuid.uuid4())

    assert exc.value.status_code == 402
    assert exc.value.details["required_tier"] == "premium"
    assert provider.calls == 0, "entitlement check ran after the model call"


async def test_premium_tier_gets_a_review() -> None:
    provider = FakeProvider()
    service = DesignReviewService(provider)

    result = await service.review(
        _submission(), entitlements=_PREMIUM, user_id=uuid.uuid4()
    )

    assert result.review.overall_score == 71.0
    assert result.prompt_version == "design-review/v1"
    assert result.input_tokens == 1200
    assert provider.calls == 1


async def test_system_prompt_is_cached() -> None:
    """Interview/review system prompts repeat verbatim; caching them is the
    dominant cost lever, so a regression here is expensive and silent."""
    provider = FakeProvider()
    await DesignReviewService(provider).review(
        _submission(), entitlements=_PREMIUM, user_id=uuid.uuid4()
    )

    assert provider.last_request is not None
    assert provider.last_request.cache_system is True
    assert provider.last_request.system


async def test_oversized_canvas_is_rejected() -> None:
    provider = FakeProvider()
    service = DesignReviewService(provider)

    with pytest.raises(ValidationError):
        await service.review(
            _submission(components=[f"node-{i}" for i in range(500)]),
            entitlements=_PREMIUM,
            user_id=uuid.uuid4(),
        )

    assert provider.calls == 0


def test_sanitizer_strips_constraints_structured_outputs_rejects() -> None:
    blob = json.dumps(_sanitize_schema(DesignReview.model_json_schema()))
    for keyword in ("minimum", "maximum", "minLength", "maxItems", "pattern"):
        assert f'"{keyword}"' not in blob


def test_sanitizer_preserves_what_the_grammar_requires() -> None:
    raw = DesignReview.model_json_schema()
    clean = _sanitize_schema(raw)
    assert isinstance(clean, dict)
    # additionalProperties: false and `required` are mandatory for strict decoding.
    assert '"additionalProperties"' in json.dumps(clean)
    assert clean["required"] == raw["required"]


def test_ranges_still_enforced_after_stripping() -> None:
    """Stripping the keyword must not lose the check — Pydantic still validates."""
    with pytest.raises(PydanticValidationError):
        DimensionScore(dimension="caching", score=150.0, rationale="out of range")


def test_empty_canvas_is_described_to_the_model() -> None:
    """A blank canvas must not read as 'no information'; the model needs to see
    that nothing was drawn so it scores low rather than hallucinating a design."""
    prompt = build_review_prompt(_submission(components=[], connections=[]))
    assert "no components placed" in prompt
    assert "no connections drawn" in prompt
