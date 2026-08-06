"""
Dual LLM provider abstraction (Anthropic + OpenAI).

Pure functions matching project convention. Supports streaming and non-streaming.

All calls route through the Selva inference gateway (OpenAI-compatible ``/v1``);
per the ecosystem convention, service code does not talk directly to Anthropic
or OpenAI. The gateway URL comes from ``SELVA_BASE_URL`` (or an explicit
``AI_BASE_URL`` override); if neither is set the call fails closed.
"""
import logging
from collections.abc import Iterator

from config import Config

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def _resolve_base_url() -> str:
    """Return the Selva gateway URL, or fail closed to prevent direct calls."""
    base = Config.AI_BASE_URL or getattr(Config, "SELVA_BASE_URL", "")
    if not base:
        raise RuntimeError(
            "LLM calls must route through the Selva inference gateway. Set "
            "SELVA_BASE_URL (or AI_BASE_URL) to the OpenAI-compatible /v1 "
            "endpoint; direct calls to Anthropic/OpenAI are disallowed by the "
            "ecosystem inference convention."
        )
    return base


def get_provider() -> str:
    return Config.AI_PROVIDER


def _get_model() -> str:
    return Config.AI_MODEL or DEFAULT_MODELS.get(get_provider(), "claude-sonnet-4-20250514")


def stream_chat(messages: list[dict], system: str = "", max_tokens: int | None = None) -> Iterator[str]:
    """Yield text chunks from the LLM. Messages are [{"role": ..., "content": ...}]."""
    max_tokens = max_tokens or Config.AI_MAX_TOKENS
    provider = get_provider()

    if provider == "anthropic":
        yield from _stream_anthropic(messages, system, max_tokens)
    elif provider == "openai":
        yield from _stream_openai(messages, system, max_tokens)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


def complete_chat(messages: list[dict], system: str = "", max_tokens: int | None = None) -> str:
    """Non-streaming completion. Returns full text response."""
    return "".join(stream_chat(messages, system, max_tokens))


def _stream_anthropic(messages: list[dict], system: str, max_tokens: int) -> Iterator[str]:
    import anthropic

    client = anthropic.Anthropic(
        api_key=Config.AI_API_KEY,
        base_url=_resolve_base_url(),
    )
    with client.messages.stream(
        model=_get_model(),
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        yield from stream.text_stream


def _stream_openai(messages: list[dict], system: str, max_tokens: int) -> Iterator[str]:
    import openai

    client = openai.OpenAI(
        api_key=Config.AI_API_KEY,
        base_url=_resolve_base_url(),
    )
    oai_messages = []
    if system:
        oai_messages.append({"role": "system", "content": system})
    oai_messages.extend(messages)

    response = client.chat.completions.create(
        model=_get_model(),
        max_tokens=max_tokens,
        messages=oai_messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
