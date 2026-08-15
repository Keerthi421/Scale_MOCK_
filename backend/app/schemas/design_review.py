"""Structured output schema for AI system-design review.

This schema is the contract with the model — `output_config.format` constrains
generation to it, and a response that fails validation is rejected at the
boundary rather than written to the database.

Note the JSON-Schema constraints Anthropic's structured outputs do NOT enforce
(`minimum`, `maximum`, `minLength`, and friends). Pydantic still validates them
client-side, so scores are range-checked here even though the constraint is
stripped from the schema sent to the model.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class DesignDimension(StrEnum):
    SCALABILITY = "scalability"
    AVAILABILITY = "availability"
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    DATA_MODELING = "data_modeling"
    CACHING = "caching"
    MESSAGING = "messaging"
    FAULT_TOLERANCE = "fault_tolerance"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    COST = "cost"


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: DesignDimension
    score: float = Field(ge=0, le=100)
    rationale: str = Field(description="Two or three sentences justifying the score.")


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    title: str
    # The component this concerns, matching a node label on the canvas where
    # one applies. Lets the UI highlight the offending node in the diagram.
    component: str | None = None
    explanation: str
    recommendation: str


class Tradeoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(description="The choice the candidate made.")
    benefit: str
    cost: str
    alternative: str = Field(description="A defensible alternative and when to prefer it.")


class CapacityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(description="e.g. 'write QPS', 'storage at 5 years'.")
    candidate_estimate: str | None = Field(
        default=None, description="Null when the candidate never estimated this."
    )
    assessment: str


class DesignReview(BaseModel):
    """The complete review the client renders as a report."""

    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0, le=100)
    summary_md: str = Field(description="Two-paragraph verdict in Markdown.")

    dimension_scores: list[DimensionScore]
    issues: list[Issue] = Field(description="Ordered most severe first.")
    tradeoffs: list[Tradeoff]
    capacity_checks: list[CapacityCheck]

    missing_components: list[str] = Field(
        description="Components the design needs but does not have."
    )
    bottlenecks: list[str]
    single_points_of_failure: list[str]

    strengths: list[str]
    next_steps: list[str] = Field(description="Concrete, ordered study actions.")
