"""
Single-part dispatch to the render worker, for routes that are not /api/render.

`/api/render` and `/api/render-stream` drive the render worker through
`render_orchestrator.render_parts_sync` / `render_parts_stream`, which also own
caching, static parts and the multi-part progress envelope. A few routes render
outside that envelope — the animation flipbook renders N frames of the same
part list, and the git HEAD preview renders the committed tree instead of the
working one. They used to call the engines in the API process. They now queue
one task per part on the same `RENDER_QUEUE`, wait on the same
`render:<job_id>` / `render:<job_id>:final` channels, and receive the same
terminal events as every other render, so there is exactly one place an engine
runs: the render worker.

The task is the worker's ordinary sync task (`stream: False`) with two optional
fields the worker honours:

* ``payload["cache_write"] = False`` — the result is not written to the render
  cache. A frame or a HEAD preview is not the render `/api/render` would have
  produced for that cache key (a HEAD render would otherwise be served for the
  working tree's file of the same name).
* ``task["source"] = {"kind": "git_head", "entry": <path in the cartridge>}`` —
  the worker materialises the cartridge's committed HEAD in a private temporary
  directory, renders ``entry`` from it, and removes it when the job ends. The
  project directory is resolved by the worker from ``payload["project_slug"]``;
  no filesystem path is taken from the queue for it.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field

from services.engine import render_orchestrator
from services.engine.render_contract import (
    RENDER_EVENT_CANCELLED,
    RENDER_EVENT_ERROR,
    RENDER_EVENT_PART_DONE,
    build_render_event,
    is_terminal_render_event,
    render_channel_for_job,
    render_final_channel_for_job,
)

#: ``task["source"]["kind"]`` for a render of the cartridge's committed HEAD.
SOURCE_GIT_HEAD = "git_head"

#: ``source_error`` on an error event: the worker could not produce the task's
#: source tree (no repository, a failed checkout, an unknown kind) ...
SOURCE_ERROR_UNAVAILABLE = "unavailable"
#: ... the entry file is not in that tree ...
SOURCE_ERROR_MISSING = "missing"
#: ... or the entry resolves outside it.
SOURCE_ERROR_OUTSIDE = "outside"

WORKER_UNAVAILABLE = "Render worker unavailable or not healthy"


@dataclass
class QueuedPart:
    """A part task sitting on the render queue, subscribed to its channels."""

    job_id: str
    part: str
    _pubsub: object = field(repr=False)


def queue_worker_part(
    payload: dict,
    *,
    engine: str,
    part: str,
    scad_path: str,
    output_path: str,
    export_format: str,
    source: dict | None = None,
) -> QueuedPart:
    """Queue one part on the render worker and subscribe to its events.

    Subscribes BEFORE pushing, as `render_parts_sync` does, so a worker that
    finishes instantly cannot publish the terminal event into the void.
    The caller checks `render_orchestrator.is_render_worker_available()` first.
    """
    r = render_orchestrator.r
    job_id = str(uuid.uuid4())
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(render_channel_for_job(job_id))
    pubsub.subscribe(render_final_channel_for_job(job_id))

    task = {
        "request_id": payload.get("request_id"),
        "mode": payload.get("mode"),
        "scad_filename": payload.get("scad_filename"),
        "job_id": job_id,
        "stream": False,
        "engine": engine,
        "part": part,
        "payload": payload,
        "scad_path": scad_path,
        "output_path": output_path,
        "export_format": export_format,
    }
    if source:
        task["source"] = source
    try:
        r.rpush(render_orchestrator.RENDER_QUEUE, json.dumps(task))
    except Exception:
        pubsub.close()
        raise
    return QueuedPart(job_id=job_id, part=part, _pubsub=pubsub)


def wait_worker_part(
    queued: QueuedPart,
    timeout: float | None = None,
    poll_interval: float = 1.0,
) -> dict:
    """Block until the queued part's terminal event; return it.

    The result is one of:

    * ``{"event": "part_done", "type", "url", "size_bytes", "log"?, "viewer_url"?, ...}``
      (protocol metadata stripped, like the parts `/api/render` returns);
    * ``{"event": "error", "error": ..., "part": ..., "source_error"?: ...}``;
    * ``{"event": "cancelled", "message": ..., "part": ...}``.

    A part that outlives *timeout* is reported as an error and the worker is
    told to give up on it, exactly as `render_parts_sync` does.
    """
    if timeout is None:
        timeout = render_orchestrator.RENDER_PART_WAIT_TIMEOUT_SECONDS
    job_id, part, pubsub = queued.job_id, queued.part, queued._pubsub
    render_channel = render_channel_for_job(job_id)
    final_channel = render_final_channel_for_job(job_id)
    deadline = time.time() + timeout
    try:
        while True:
            if time.time() > deadline:
                message = "Render job timed out"
                render_orchestrator._notify_error(job_id, part, message)
                return build_render_event(RENDER_EVENT_ERROR, part=part, error=message, message=message)

            message = pubsub.get_message(timeout=poll_interval)
            if not message:
                continue
            channel = render_orchestrator._coerce_channel(message.get("channel", ""))
            event = render_orchestrator._parse_stream_payload(message.get("data"))
            if not event or channel not in (render_channel, final_channel):
                continue
            if not is_terminal_render_event(event):
                continue  # progress chatter; this caller reports per part
            if event.get("event") == RENDER_EVENT_PART_DONE:
                if not event.get("type"):
                    # The worker's raw engine `part_done` (stream path) carries
                    # no artifact; the baked one follows on the final channel.
                    continue
                done = render_orchestrator._sanitize_terminal_payload(event)
                return {"event": RENDER_EVENT_PART_DONE, **done}
            if event.get("event") == RENDER_EVENT_ERROR:
                error = event.get("error") or event.get("message") or "Render failed"
                extra = {"source_error": event["source_error"]} if event.get("source_error") else {}
                return build_render_event(RENDER_EVENT_ERROR, part=event.get("part") or part,
                                          error=error, message=error, **extra)
            return build_render_event(RENDER_EVENT_CANCELLED, part=event.get("part") or part,
                                      message=event.get("message") or "Render cancelled")
    finally:
        pubsub.close()


def render_part_on_worker(payload: dict, *, timeout: float | None = None, **task_fields) -> dict:
    """`queue_worker_part` then `wait_worker_part`; see both."""
    return wait_worker_part(queue_worker_part(payload, **task_fields), timeout=timeout)
