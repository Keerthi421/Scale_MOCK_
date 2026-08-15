"""Anthropic Claude implementation of AIProvider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.ai.base import AIRequest, AIResponse, AIStructuredResponse, AIUsage
from app.core.config import settings
from app.core.exceptions import ExternalServiceError

# JSON-Schema keywords the structured-outputs grammar does not accept. Pydantic
# still enforces them when validating the response, so stripping them here loses
# no safety — it just moves the check from the model to our side of the wire.
# This mirrors what the SDK's `messages.parse()` helper does automatically; we
# build the schema by hand, so we have to do it ourselves.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
    }
)


def _sanitize_schema(node: object) -> object:
    """Recursively drop constraint keywords structured outputs rejects."""
    if isinstance(node, dict):
        return {
            k: _sanitize_schema(v)
            for k, v in node.items()
            if k not in _UNSUPPORTED_SCHEMA_KEYS
        }
    if isinstance(node, list):
        return [_sanitize_schema(v) for v in node]
    return node


def _usage_from(raw: object) -> AIUsage:
    return AIUsage(
        input_tokens=getattr(raw, "input_tokens", 0) or 0,
        output_tokens=getattr(raw, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(raw, "cache_read_input_tokens", 0) or 0,
    )


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or settings.ANTHROPIC_API_KEY
        if not key:
            raise ExternalServiceError(
                "ANTHROPIC_API_KEY is not configured; AI features are unavailable"
            )
        self._client = AsyncAnthropic(api_key=key)
        self._model = model or settings.ANTHROPIC_MODEL

    @property
    def model_id(self) -> str:
        return self._model

    def _build(self, request: AIRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": request.max_tokens,
            "output_config": {"effort": request.effort},
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.system:
            if request.cache_system:
                # Cache the system prefix: interview prompts are long and byte-identical
                # across every turn of a session, so this is the dominant cost lever.
                payload["system"] = [
                    {
                        "type": "text",
                        "text": request.system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                payload["system"] = request.system
        return payload

    async def generate(self, request: AIRequest) -> AIResponse:
        try:
            response = await self._client.messages.create(**self._build(request))  # type: ignore[arg-type]
        except RateLimitError as exc:
            raise ExternalServiceError("AI provider rate limit reached") from exc
        except (APIStatusError, APIConnectionError) as exc:
            raise ExternalServiceError("AI provider request failed") from exc

        # Classifiers can decline with HTTP 200 and empty content. Check this
        # before reading content, or the caller silently gets an empty answer.
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            return AIResponse(
                text="",
                usage=_usage_from(response.usage),
                model=response.model,
                refused=True,
                refusal_category=category,
            )

        text = "".join(b.text for b in response.content if b.type == "text")
        return AIResponse(text=text, usage=_usage_from(response.usage), model=response.model)

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(**self._build(request)) as stream:  # type: ignore[arg-type]
                async for chunk in stream.text_stream:
                    yield chunk
        except RateLimitError as exc:
            raise ExternalServiceError("AI provider rate limit reached") from exc
        except (APIStatusError, APIConnectionError) as exc:
            raise ExternalServiceError("AI provider stream failed") from exc

    async def generate_structured[T: BaseModel](
        self, request: AIRequest, schema: type[T]
    ) -> AIStructuredResponse[T]:
        payload = self._build(request)
        payload["output_config"] = {
            "effort": request.effort,
            "format": {
                "type": "json_schema",
                "schema": _sanitize_schema(schema.model_json_schema()),
            },
        }

        try:
            # Streaming: evaluation responses are long, and a non-streaming call
            # at this max_tokens risks an HTTP timeout.
            async with self._client.messages.stream(**payload) as stream:  # type: ignore[arg-type]
                response = await stream.get_final_message()
        except RateLimitError as exc:
            raise ExternalServiceError("AI provider rate limit reached") from exc
        except (APIStatusError, APIConnectionError) as exc:
            raise ExternalServiceError("AI provider request failed") from exc

        if response.stop_reason == "refusal":
            raise ExternalServiceError("AI provider declined to evaluate this submission")
        if response.stop_reason == "max_tokens":
            # The JSON is truncated and will not parse; a clear error beats a
            # confusing validation failure.
            raise ExternalServiceError("AI response exceeded the token budget; raise max_tokens")

        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            data = schema.model_validate_json(text)
        except ValidationError as exc:
            raise ExternalServiceError(
                "AI returned a response that did not match the expected schema"
            ) from exc

        return AIStructuredResponse(
            data=data, usage=_usage_from(response.usage), model=response.model
        )
