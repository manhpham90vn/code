"""Model definitions, pricing, and token usage tracking."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from .context import Context

DEFAULT_MODEL = "claude-opus-4-6"


class Model(str, Enum):
    """Supported Claude models."""

    OPUS = "claude-opus-4-6"
    SONNET = "claude-sonnet-4-6"

    @property
    def description(self) -> str:
        return _MODEL_DESCRIPTIONS[self]


_MODEL_DESCRIPTIONS: dict[Model, str] = {
    Model.OPUS: "Claude Opus 4.6 (most capable)",
    Model.SONNET: "Claude Sonnet 4.6 (balanced)",
}

# USD per 1M tokens: (input, output, cache_write, cache_read)
_Pricing = tuple[float, float, float, float]

MODEL_PRICING: dict[Model, _Pricing] = {
    Model.OPUS: (5.00, 25.00, 6.25, 0.50),
    Model.SONNET: (3.00, 15.00, 3.75, 0.30),
}

# Fallback pricing when model not found
_DEFAULT_PRICING: _Pricing = MODEL_PRICING[Model.OPUS]


def get_model_pricing(model: str) -> _Pricing:
    """Get pricing for a model. Falls back to Opus pricing if not found."""
    match model:
        case Model.OPUS:
            return MODEL_PRICING[Model.OPUS]
        case Model.SONNET:
            return MODEL_PRICING[Model.SONNET]
        case _:
            return _DEFAULT_PRICING


def calc_cost(
    input_tokens: int,
    output_tokens: int,
    cache_create: int,
    cache_read: int,
    model: str,
) -> float:
    """Calculate cost in USD for given token counts."""
    input_price, output_price, cache_write_price, cache_read_price = get_model_pricing(model)
    return (
        (input_tokens / 1_000_000) * input_price
        + (output_tokens / 1_000_000) * output_price
        + (cache_create / 1_000_000) * cache_write_price
        + (cache_read / 1_000_000) * cache_read_price
    )


def log_token_usage(
    response: object,
    model: str | None = None,
    context: Context | None = None,
    console: Console | None = None,
) -> None:
    """Log token usage, estimated cost, and accumulate totals in context."""
    if model is None:
        model = DEFAULT_MODEL

    usage = response.usage  # type: ignore[attr-defined]
    input_tokens: int = usage.input_tokens
    output_tokens: int = usage.output_tokens
    cache_create: int = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read: int = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Accumulate in context
    if context:
        context.add_usage(input_tokens, output_tokens, cache_create, cache_read)

    req_cost = calc_cost(input_tokens, output_tokens, cache_create, cache_read, model)

    parts: list[str] = [
        f"{input_tokens} in / {output_tokens} out",
    ]
    if cache_create or cache_read:
        parts.append(f"cache: {cache_create} write / {cache_read} read")
    parts.append(f"${req_cost:.4f}")

    # Show running total
    if context:
        session_cost = calc_cost(
            context.total_input_tokens,
            context.total_output_tokens,
            context.total_cache_create_tokens,
            context.total_cache_read_tokens,
            model,
        )
        parts.append(f"total: ${session_cost:.4f}")

    if console:
        console.print(f"[dim]📊 {' | '.join(parts)}[/dim]")
