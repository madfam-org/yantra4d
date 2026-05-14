"""
Render stream contracts and Redis channel helpers.

These helpers centralize stream event schema and channel construction so
producer and consumer remain in sync during refactors.
"""

from __future__ import annotations

RENDER_STREAM_SCHEMA_VERSION = "1.0.0"

RENDER_CHANNEL_PREFIX = "render"
RENDER_FINAL_CHANNEL_SUFFIX = "final"

RENDER_EVENT_PART_DONE = "part_done"
RENDER_EVENT_ERROR = "error"
RENDER_EVENT_CANCELLED = "cancelled"
RENDER_EVENT_COMPLETE = "complete"
RENDER_EVENT_OUTPUT = "output"
RENDER_EVENT_PART_START = "part_start"


def render_channel_for_job(job_id: str) -> str:
    """Return Redis channel name for a render job's progress stream."""
    return f"{RENDER_CHANNEL_PREFIX}:{job_id}"


def render_final_channel_for_job(job_id: str) -> str:
    """Return Redis channel for render job terminal events."""
    return f"{render_channel_for_job(job_id)}:{RENDER_FINAL_CHANNEL_SUFFIX}"


def build_render_event(event: str, **payload) -> dict:
    """Build a versioned render event payload."""
    event_payload = {
        "stream_protocol": RENDER_STREAM_SCHEMA_VERSION,
        "event": event,
    }
    event_payload.update(payload)
    return event_payload


def is_terminal_render_event(event_payload: dict | None) -> bool:
    """Return True when event payload indicates final job outcome."""
    if not isinstance(event_payload, dict):
        return False
    return event_payload.get("event") in {
        RENDER_EVENT_PART_DONE,
        RENDER_EVENT_ERROR,
        RENDER_EVENT_CANCELLED,
    }

