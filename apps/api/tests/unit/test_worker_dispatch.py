"""services.engine.worker_dispatch: one part, queued and awaited."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inline_render_worker import InlineRenderRedis

from services.engine import render_orchestrator, worker_dispatch
from services.engine.render_contract import (
    build_render_event,
    render_channel_for_job,
    render_final_channel_for_job,
)

PAYLOAD = {"project_slug": "p", "scad_filename": "m.scad", "mode": "default", "request_id": "req-1"}
FIELDS = {"engine": "openscad", "part": "body", "scad_path": "/x/m.scad",
          "output_path": "/s/o.stl", "export_format": "stl"}


@pytest.fixture
def redis(monkeypatch):
    fake = InlineRenderRedis(render_orchestrator.RENDER_QUEUE, run_inline=False)
    monkeypatch.setattr(render_orchestrator, "r", fake)
    return fake


def _queued(redis, **extra):
    queued = worker_dispatch.queue_worker_part(PAYLOAD, **FIELDS, **extra)
    (raw,) = redis.lists[render_orchestrator.RENDER_QUEUE]
    return queued, json.loads(raw)


def test_task_is_the_workers_sync_task(redis):
    queued, task = _queued(redis, source={"kind": "git_head", "entry": "m.scad"})
    assert task["job_id"] == queued.job_id
    assert task["stream"] is False
    assert task["request_id"] == "req-1"
    assert {k: task[k] for k in FIELDS} == FIELDS
    assert task["source"] == {"kind": "git_head", "entry": "m.scad"}
    assert task["payload"] == PAYLOAD


def test_subscribes_before_pushing(redis):
    """A worker that answers instantly must not publish into the void."""
    queued, _task = _queued(redis)
    assert any(render_final_channel_for_job(queued.job_id) in sub.channels for sub in redis.subscribers)


def test_returns_the_baked_part_and_skips_engine_chatter(redis):
    queued, _task = _queued(redis)
    channel = render_channel_for_job(queued.job_id)
    redis.publish(channel, json.dumps(build_render_event("output", part="body", line="x")))
    # The engine's own part_done has no artifact; the worker's baked one does.
    redis.publish(channel, json.dumps(build_render_event("part_done", part="body", progress=100)))
    redis.publish(render_final_channel_for_job(queued.job_id), json.dumps(build_render_event(
        "part_done", part="body", type="body", url="/static/o.stl", size_bytes=3, log="[body] ok\n",
    )))
    result = worker_dispatch.wait_worker_part(queued, timeout=1, poll_interval=0)
    assert result["event"] == "part_done"
    assert result["url"] == "/static/o.stl"
    assert "stream_protocol" not in result
    assert redis.subscribers == []  # closed


def test_error_keeps_the_source_error_code(redis):
    queued, _task = _queued(redis)
    redis.publish(render_final_channel_for_job(queued.job_id), json.dumps(build_render_event(
        "error", part="body", error="SCAD file does not exist in HEAD", source_error="missing",
    )))
    result = worker_dispatch.wait_worker_part(queued, timeout=1, poll_interval=0)
    assert result["event"] == "error"
    assert result["error"] == "SCAD file does not exist in HEAD"
    assert result["source_error"] == "missing"


def test_cancelled(redis):
    queued, _task = _queued(redis)
    redis.publish(render_final_channel_for_job(queued.job_id), json.dumps(build_render_event(
        "cancelled", part="body", message="Render cancelled by user request",
    )))
    result = worker_dispatch.wait_worker_part(queued, timeout=1, poll_interval=0)
    assert result["event"] == "cancelled"


def test_timeout_is_an_error_and_tells_the_worker(redis):
    queued, _task = _queued(redis)
    result = worker_dispatch.wait_worker_part(queued, timeout=0, poll_interval=0)
    assert result["event"] == "error"
    assert result["error"] == "Render job timed out"
    told = [payload for channel, payload in redis.published
            if channel == render_final_channel_for_job(queued.job_id)]
    assert told and told[-1]["event"] == "error"


def test_push_failure_closes_the_subscription(redis, monkeypatch):
    def boom(*_a):
        raise ConnectionError("redis down")
    monkeypatch.setattr(redis, "rpush", boom)
    with pytest.raises(ConnectionError):
        worker_dispatch.queue_worker_part(PAYLOAD, **FIELDS)
    assert redis.subscribers == []
