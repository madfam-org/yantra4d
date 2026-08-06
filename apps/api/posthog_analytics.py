"""PostHog analytics for Yantra4D — graceful no-op when API key is empty."""

import os

_client: object | None = None


def init_posthog() -> None:
    global _client
    api_key = os.environ.get("POSTHOG_API_KEY", "")
    if not api_key:
        return
    try:
        import posthog
        posthog.api_key = api_key
        posthog.host = os.environ.get("POSTHOG_HOST", "https://analytics.yantra4d.com")
        _client = posthog
    except ImportError:
        pass


def track(distinct_id: str, event: str, properties: dict | None = None) -> None:
    if _client is None:
        return
    try:
        _client.capture(distinct_id, event, properties=properties or {})
    except Exception:
        pass


def shutdown() -> None:
    if _client is None:
        return
    try:
        _client.shutdown()
    except Exception:
        pass
