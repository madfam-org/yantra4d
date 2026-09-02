"""`POST /api/render-cancel` cancels the caller's own render, not everyone's.

Residual finding from the WebSocket render-channel fix: the HTTP cancel route was
`@optional_auth` + `@require_render_scope` (log mode → allow) over
`cancel_all_renders()`, with no body at all. An anonymous POST over plain HTTP
therefore terminated every queued and active render on the single backend
replica — the same blast radius the WS channel had, one door along.

The fix gives a render an identity the client can hold: `/api/render-stream`
publishes a `job` event carrying `{request_id, job_ids}`, and cancel acts only on
the ids it is given. Knowing a server-minted UUID4 `job_id` is what stands in for
the ownership the render pipeline does not record, which is why the route can
stay open to anonymous callers.
"""
import json
from pathlib import Path

import pytest

ADMIN_CLAIMS = {"sub": "admin-1", "roles": ["admin"], "yantra4d_tier": "madfam"}
USER_CLAIMS = {"sub": "user-1", "roles": ["user"], "yantra4d_tier": "pro"}


class FakeRedis:
    """In-memory stand-in covering the calls the cancel paths make."""

    def __init__(self):
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.published: list[tuple[str, str]] = []

    # strings
    def get(self, key):
        return self.strings.get(key)

    def set(self, key, value, ex=None):
        self.strings[key] = value

    def delete(self, key):
        self.strings.pop(key, None)

    # lists
    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def lrange(self, key, start, end):
        return list(self.lists.get(key, []))

    def lrem(self, key, count, value):
        entries = self.lists.get(key, [])
        if value in entries:
            entries.remove(value)

    def llen(self, key):
        return len(self.lists.get(key, []))

    # sets
    def sadd(self, key, member):
        self.sets.setdefault(key, set()).add(member)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def srem(self, key, member):
        self.sets.get(key, set()).discard(member)

    def publish(self, channel, message):
        self.published.append((channel, message))

    def pubsub(self, **_kwargs):  # pragma: no cover - streams are not exercised here
        raise AssertionError("cancel paths must not open a pubsub connection")


@pytest.fixture
def orch(monkeypatch):
    from services.engine import render_orchestrator

    fake = FakeRedis()
    monkeypatch.setattr(render_orchestrator, "r", fake)
    render_orchestrator.fake = fake  # convenience handle for the tests
    return render_orchestrator


def _queue(orch, *, job_id, request_id, part="body", engine="openscad"):
    """Put a task on the render queue exactly as the render loop would."""
    task = {
        "job_id": job_id,
        "request_id": request_id,
        "part": part,
        "engine": engine,
        "stream": True,
    }
    orch.r.rpush(orch.RENDER_QUEUE, json.dumps(task))
    return task


def _activate(orch, *, job_id, request_id, part="body", engine="openscad"):
    """Mark a job active exactly as apps/worker/render_worker.py::_set_active_job does."""
    orch.r.sadd(orch.ACTIVE_RENDER_JOBS_KEY, job_id)
    orch.r.set(
        f"{orch.ACTIVE_RENDER_META_PREFIX}{job_id}",
        json.dumps({"job_id": job_id, "request_id": request_id, "part": part, "engine": engine}),
    )


def _cancel_key(orch, job_id):
    return f"{orch.CANCEL_JOB_PREFIX}{job_id}"


# ──────────────────────────────────────────────
# 1. The mechanism: per-job cancellation is the one the worker already polls
# ──────────────────────────────────────────────

WORKER_SOURCE = (
    Path(__file__).resolve().parents[3] / "worker" / "render_worker.py"
).read_text()


def test_the_worker_still_polls_the_per_job_cancel_key_scoped_cancel_sets(orch):
    """The API and the worker must agree on the key, or cancel is a silent no-op.

    apps/worker/render_worker.py::_is_cancelled reads CANCEL_ALL_KEY and
    CANCEL_JOB_PREFIX + job_id, and passes `lambda: _is_cancelled(job_id)` into
    each engine as its cancellation poll. Scoped cancel sets that second key, so
    the worker needs no change — but it resolves the prefix independently, via
    getattr with a literal fallback, so pin the two together here.
    """
    assert 'f"{CANCEL_JOB_PREFIX}{job_id}"' in WORKER_SOURCE
    assert "is_cancelled=lambda: _is_cancelled(job_id)" in WORKER_SOURCE


def test_worker_and_orchestrator_share_the_cancel_keyspace(orch):
    """Pin the literal defaults the worker falls back to against the real ones."""
    assert orch.CANCEL_JOB_PREFIX == "yantra_render_cancel_job:"
    assert orch.CANCEL_ALL_KEY == "yantra_render_cancel_all"
    assert orch.ACTIVE_RENDER_JOBS_KEY == "yantra_render_active_jobs"
    for literal in (
        f'"{orch.CANCEL_JOB_PREFIX}"',
        f'"{orch.CANCEL_ALL_KEY}"',
        f'"{orch.ACTIVE_RENDER_JOBS_KEY}"',
    ):
        assert literal in WORKER_SOURCE, f"worker fallback drifted from {literal}"


def test_cancel_render_jobs_marks_only_the_named_active_job(orch):
    _activate(orch, job_id="mine", request_id="req-a")
    _activate(orch, job_id="theirs", request_id="req-b")

    cancelled = orch.cancel_render_jobs(["mine"])

    assert cancelled == ["mine"]
    assert orch.r.get(_cancel_key(orch, "mine")) == "1"
    assert orch.r.get(_cancel_key(orch, "theirs")) is None
    # The global switch is never touched by a scoped cancel.
    assert orch.r.get(orch.CANCEL_ALL_KEY) is None


def test_cancel_render_jobs_prunes_only_the_named_queue_entry(orch):
    _queue(orch, job_id="mine", request_id="req-a")
    _queue(orch, job_id="theirs", request_id="req-b")

    orch.cancel_render_jobs(["mine"])

    remaining = [json.loads(t)["job_id"] for t in orch.r.lrange(orch.RENDER_QUEUE, 0, -1)]
    assert remaining == ["theirs"]


def test_cancel_render_jobs_notifies_only_the_cancelled_job(orch):
    _activate(orch, job_id="mine", request_id="req-a", part="lid")
    _activate(orch, job_id="theirs", request_id="req-b")

    orch.cancel_render_jobs(["mine"])

    channels = {channel for channel, _ in orch.r.published}
    assert channels == {"render:mine", "render:mine:final"}
    payload = json.loads(orch.r.published[0][1])
    assert payload["event"] == "cancelled"
    assert payload["part"] == "lid"


def test_cancel_render_jobs_ignores_unknown_ids(orch):
    _activate(orch, job_id="theirs", request_id="req-b")

    assert orch.cancel_render_jobs(["does-not-exist"]) == []
    assert orch.r.get(_cancel_key(orch, "theirs")) is None


def test_cancel_render_jobs_with_no_ids_touches_nothing(orch):
    _activate(orch, job_id="theirs", request_id="req-b")

    assert orch.cancel_render_jobs([]) == []
    assert orch.r.get(_cancel_key(orch, "theirs")) is None
    assert orch.r.get(orch.CANCEL_ALL_KEY) is None
    assert orch.r.published == []


# ──────────────────────────────────────────────
# 2. Request-scoped cancel also stops parts that are not queued yet
# ──────────────────────────────────────────────

def test_cancel_request_marks_every_job_of_that_request_only(orch):
    _activate(orch, job_id="a1", request_id="req-a", part="body")
    _queue(orch, job_id="a2", request_id="req-a", part="lid")
    _activate(orch, job_id="b1", request_id="req-b")

    cancelled = orch.cancel_request("req-a")

    assert set(cancelled) == {"a1", "a2"}
    assert orch.r.get(_cancel_key(orch, "a1")) == "1"
    assert orch.r.get(_cancel_key(orch, "b1")) is None
    remaining = [json.loads(t)["job_id"] for t in orch.r.lrange(orch.RENDER_QUEUE, 0, -1)]
    assert remaining == []


def test_cancel_request_sets_the_flag_the_render_loop_polls(orch):
    orch.cancel_request("req-a")

    assert orch.is_request_cancelled("req-a") is True
    assert orch.is_request_cancelled("req-b") is False


def test_cancel_request_with_nothing_queued_still_arms_the_flag(orch):
    """A cancel between two parts has no job to mark, but must still take."""
    assert orch.cancel_request("req-a") == []
    assert orch.is_request_cancelled("req-a") is True


def test_a_new_render_supersedes_a_stale_cancel_for_a_reused_request_id(orch):
    orch.cancel_request("req-a")
    assert orch.is_request_cancelled("req-a") is True

    orch.clear_request_cancel("req-a")

    assert orch.is_request_cancelled("req-a") is False


def test_is_request_cancelled_is_false_without_a_request_id(orch):
    assert orch.is_request_cancelled(None) is False
    assert orch.is_request_cancelled("") is False


def test_a_job_whose_metadata_expired_is_not_cancelled_by_request_id(orch):
    """Unattributable work is left alone rather than swept up."""
    orch.r.sadd(orch.ACTIVE_RENDER_JOBS_KEY, "orphan")

    assert orch.cancel_request("req-a") == []
    assert orch.r.get(_cancel_key(orch, "orphan")) is None
    # ...but its own job_id still cancels it.
    assert orch.cancel_render_jobs(["orphan"]) == ["orphan"]


# ──────────────────────────────────────────────
# 3. cancel_all_renders keeps its old behaviour, now admin-only over HTTP
# ──────────────────────────────────────────────

def test_cancel_all_renders_still_sweeps_everything(orch):
    _activate(orch, job_id="a1", request_id="req-a")
    _queue(orch, job_id="b1", request_id="req-b")

    assert orch.cancel_all_renders() is True
    assert orch.r.get(orch.CANCEL_ALL_KEY) is not None
    assert orch.r.get(_cancel_key(orch, "a1")) == "1"
    assert orch.r.lrange(orch.RENDER_QUEUE, 0, -1) == []


# ──────────────────────────────────────────────
# 4. The stream hands the client its cancellation identity
# ──────────────────────────────────────────────

def _stream_payload(parts):
    return {
        "parts": parts,
        "stl_prefix": "test_",
        "export_format": "stl",
        "project_slug": "sample",
        "scad_filename": "sample.scad",
        "params": {},
        "static_stl_map": {},
        "request_id": "req-stream",
    }


def _events(stream):
    return [json.loads(chunk.split("data: ", 1)[1].strip()) for chunk in stream]


def test_stream_opens_with_a_job_event_carrying_the_request_id(orch, monkeypatch):
    monkeypatch.setattr(orch, "is_render_worker_available", lambda: False)

    events = _events(orch.render_parts_stream(
        {}, _stream_payload(["body"]), "openscad", "/tmp/s.scad", "stl",
    ))

    assert events[0]["event"] == "job"
    assert events[0]["request_id"] == "req-stream"
    assert events[0]["job_ids"] == []
    # Additive contract bump, so a 1.0.0 consumer keeps working.
    assert events[0]["stream_protocol"] == orch.RENDER_STREAM_SCHEMA_VERSION


def test_stream_stops_queueing_further_parts_once_the_request_is_cancelled(orch, monkeypatch):
    """The gap job_ids alone cannot close: parts are queued one at a time."""
    monkeypatch.setattr(orch, "is_render_worker_available", lambda: False)
    orch.r.set(f"{orch.CANCEL_REQUEST_PREFIX}req-stream", "1")

    # clear_request_cancel() runs first, so re-arm it after the stream opens.
    stream = orch.render_parts_stream(
        {}, _stream_payload(["body", "lid"]), "openscad", "/tmp/s.scad", "stl",
    )
    first = json.loads(next(stream).split("data: ", 1)[1].strip())
    assert first["event"] == "job"

    orch.r.set(f"{orch.CANCEL_REQUEST_PREFIX}req-stream", "1")
    rest = _events(stream)

    assert rest[0]["event"] == "cancelled"
    assert rest[0]["reason"] == "user_request"
    # Nothing was queued, and the stream still terminates with `complete`.
    assert orch.r.lrange(orch.RENDER_QUEUE, 0, -1) == []
    assert rest[-1]["event"] == "complete"


def test_stream_clears_a_stale_cancel_flag_before_rendering(orch, monkeypatch):
    monkeypatch.setattr(orch, "is_render_worker_available", lambda: False)
    orch.r.set(f"{orch.CANCEL_REQUEST_PREFIX}req-stream", "1")

    _events(orch.render_parts_stream(
        {}, _stream_payload(["body"]), "openscad", "/tmp/s.scad", "stl",
    ))

    assert orch.is_request_cancelled("req-stream") is False


# ──────────────────────────────────────────────
# 5. The route: a target is required, and `all` is admin-only
# ──────────────────────────────────────────────

@pytest.fixture
def client(tmp_path):
    from app import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def route_orch(monkeypatch):
    """Patch the Redis the route's orchestrator calls reach."""
    from services.engine import render_orchestrator

    fake = FakeRedis()
    monkeypatch.setattr(render_orchestrator, "r", fake)
    return render_orchestrator


def test_anonymous_cancel_without_a_target_is_rejected(client):
    res = client.post("/api/render-cancel")

    assert res.status_code == 400
    body = res.get_json()
    assert body["error_code"] == "cancel_target_required"


def test_anonymous_cancel_with_an_empty_json_object_is_rejected(client):
    res = client.post("/api/render-cancel", json={})

    assert res.status_code == 400
    assert res.get_json()["error_code"] == "cancel_target_required"


def test_cancel_with_a_job_id_cancels_only_that_job(client, route_orch):
    _activate(route_orch, job_id="mine", request_id="req-a")
    _activate(route_orch, job_id="theirs", request_id="req-b")

    res = client.post("/api/render-cancel", json={"job_ids": ["mine"]})

    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "cancelled"
    assert body["cancelled"] is True
    assert body["cancelled_jobs"] == ["mine"]
    assert route_orch.r.get(_cancel_key(route_orch, "theirs")) is None
    assert route_orch.r.get(route_orch.CANCEL_ALL_KEY) is None


def test_cancel_with_a_request_id_cancels_only_that_request(client, route_orch):
    _activate(route_orch, job_id="mine", request_id="req-a")
    _activate(route_orch, job_id="theirs", request_id="req-b")

    res = client.post("/api/render-cancel", json={"request_id": "req-a"})

    assert res.status_code == 200
    assert res.get_json()["cancelled_jobs"] == ["mine"]
    assert route_orch.r.get(_cancel_key(route_orch, "theirs")) is None


def test_cancel_reports_a_request_scoped_cancel_even_with_no_live_jobs(client, route_orch):
    res = client.post("/api/render-cancel", json={"request_id": "req-a"})

    body = res.get_json()
    assert body["status"] == "cancelled"
    assert body["cancelled"] is True
    assert body["cancelled_jobs"] == []


@pytest.mark.parametrize("body", [
    {"job_ids": "not-a-list"},
    {"job_ids": [""]},
    {"job_ids": [123]},
    {"job_ids": ["x"] * 65},
    {"request_id": ""},
    {"request_id": 7},
])
def test_malformed_targets_are_rejected(client, body):
    res = client.post("/api/render-cancel", json=body)

    assert res.status_code == 400
    assert res.get_json()["error_code"] == "cancel_target_invalid"


def test_all_true_is_refused_for_an_anonymous_caller(client, monkeypatch, route_orch):
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    _activate(route_orch, job_id="theirs", request_id="req-b")

    res = client.post("/api/render-cancel", json={"all": True})

    assert res.status_code == 401
    assert route_orch.r.get(route_orch.CANCEL_ALL_KEY) is None


def test_all_true_is_refused_for_a_non_admin_caller(client, monkeypatch, route_orch):
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr("middleware.auth.decode_token", lambda token: USER_CLAIMS)
    monkeypatch.setattr("middleware.auth._sync_user_from_claims", lambda claims: None)
    _activate(route_orch, job_id="theirs", request_id="req-b")

    res = client.post(
        "/api/render-cancel",
        json={"all": True},
        headers={"Authorization": "Bearer user-token"},
    )

    assert res.status_code == 403
    assert route_orch.r.get(route_orch.CANCEL_ALL_KEY) is None
    assert route_orch.r.get(_cancel_key(route_orch, "theirs")) is None


def test_all_true_is_allowed_for_an_admin(client, monkeypatch, route_orch):
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr("middleware.auth.decode_token", lambda token: ADMIN_CLAIMS)
    monkeypatch.setattr("middleware.auth._sync_user_from_claims", lambda claims: None)
    _activate(route_orch, job_id="theirs", request_id="req-b")

    res = client.post(
        "/api/render-cancel",
        json={"all": True},
        headers={"Authorization": "Bearer admin-token"},
    )

    assert res.status_code == 200
    body = res.get_json()
    assert body["scope"] == "all"
    assert body["cancelled"] is True
    assert route_orch.r.get(_cancel_key(route_orch, "theirs")) == "1"


def test_a_scoped_cancel_never_arms_the_global_switch(client, route_orch):
    client.post("/api/render-cancel", json={"request_id": "req-a"})
    client.post("/api/render-cancel", json={"job_ids": ["mine"]})

    assert route_orch.r.get(route_orch.CANCEL_ALL_KEY) is None
