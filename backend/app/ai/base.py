"""Provider-agnostic AI interface.

Nothing outside `app/ai/` imports the Anthropic SDK. Services depend on this
protocol, so swapping or A/B-testing providers is a wiring change rather than a
rewrite — and tests substitute a fake without touching the network.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel

Role = Literal["user", "assistant"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass(slots=True)
class AIMessage:
    role: Role
    content: str


@dataclass(slots=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass(slots=True)
class AIResponse:
    text: str
    usage: AIUsage
    model: str
    # True when safety classifiers declined the request. Callers must check this
    # before using `text` — a refusal returns HTTP 200 with empty content, so
    # treating it as a normal response silently yields an empty answer.
    refused: bool = False
    refusal_category: str | None = None


@dataclass(slots=True)
class AIStructuredResponse[T: BaseModel]:
    data: T
    usage: AIUsage
    model: str


@dataclass(slots=True)
class AIRequest:
    messages: Sequence[AIMessage]
    system: str | None = None
    max_tokens: int = 8192
    effort: Effort = "high"
    # Marks the stable prefix for prompt caching. Interview system prompts are
    # long and identical across turns, so caching them is the single biggest
    # cost lever in the product.
    cache_system: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class AIProvider(Protocol):
    """The contract every model backend implements."""

    @property
    def model_id(self) -> str: ...

    async def generate(self, request: AIRequest) -> AIResponse:
        """Single completion, non-streaming."""
        ...

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Yield text deltas as they arrive. Used for the live interviewer."""
        ...

    async def generate_structured[T: BaseModel](
        self, request: AIRequest, schema: type[T]
    ) -> AIStructuredResponse[T]:
        """Completion validated against a Pydantic schema.

        Used for every evaluation path (design review, interview scoring, code
        review) so a malformed model response fails loudly at the boundary
        instead of corrupting a database row.
        """
        ...
