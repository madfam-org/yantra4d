"""Free tiers re-render Commons cartridges with the B-Rep engines under a quota.

Owner decision 2026-11-20 (services/engine/commons_render_quota.py). These run
the real routes, the real payload resolution and the real rate-limiter
storage; only the render itself (the worker round trip) and the Redis lease
store are stood in for.
"""
import json
import time
from pathlib import Path

import pytest

from services.core.tier_service import check_feature, get_tier_limits
from services.engine import commons_render_quota as quota

CQ_SCRIPT = 'result = cq.Workplane("XY").box(1, 1, 1)\n'
FORK_META = {"source": {"type": "fork", "forked_from": "cq-commons"}}


def _manifest(slug: str, *, parts=("body",), engine="cadquery") -> dict:
    return {
        "project": {"slug": slug, "name": slug, "version": "1.0.0", "engine": engine},
        "modes": [{
            "id": "body", "scad_file": "main.py", "label": {"en": "Body"},
            "parts": list(parts), "engine": engine,
            "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": p, "render_mode": 0, "label": {"en": p}, "default_color": "#ffffff"} for p in parts],
        "parameters": [{"id": "size", "type": "slider", "default": 10, "min": 1, "max": 100,
                        "label": {"en": "Size"}},
                       {"id": "text", "type": "text", "default": "HELLO", "maxlength": 20,
                        "label": {"en": "Text"}}],
        "estimate_constants": {"base_time": 1, "per_unit": 1, "per_part": 1},
    }


def _cartridge(root: Path, slug: str, *, meta=None, **kwargs) -> Path:
    path = root / slug
    path.mkdir(parents=True, exist_ok=True)
    (path / "project.json").write_text(json.dumps(_manifest(slug, **kwargs)))
    (path / "main.py").write_text(CQ_SCRIPT)
    if meta is not None:
        (path / "project.meta.json").write_text(json.dumps(meta))
    return path


class FakeRedis:
    """The Redis commands the quota, the lease and the cancel sweep use.

    The four Lua scripts are run as their Python equivalents (``eval`` matches
    the exact script text); ``TestLuaScriptsOnRealRedis`` runs the real Lua
    against a real redis-server where one is installed, so the two cannot
    drift unnoticed.
    """

    def __init__(self):
        self.values: dict[str, str] = {}
        self.expiry: dict[str, float] = {}
        self.lists: dict[str, list] = {}
        self.sets: dict[str, set] = {}
        self.published: list = []

    def _live(self, key):
        at = self.expiry.get(key)
        if at is not None and at <= time.time():
            self.values.pop(key, None)
            self.expiry.pop(key, None)
        return key in self.values

    def get(self, key):
        return self.values.get(key) if self._live(key) else None

    def set(self, key, value, nx=False, ex=None):
        if nx and self._live(key):
            return None
        self.values[key] = str(value)
        if ex is not None:
            self.expiry[key] = time.time() + ex
        else:
            self.expiry.pop(key, None)
        return True

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
            self.expiry.pop(key, None)

    def ttl(self, key):
        if not self._live(key):
            return -2
        at = self.expiry.get(key)
        return -1 if at is None else max(0, round(at - time.time()))

    def lrange(self, key, _start, _end):
        return list(self.lists.get(key, []))

    def lrem(self, key, _count, value):
        self.lists[key] = [v for v in self.lists.get(key, []) if v != value]

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def publish(self, channel, message):
        self.published.append((channel, message))

    def pubsub(self, **_kwargs):
        return FakePubSub(self)

    #: Set by a test: final channel -> events the worker publishes on it.
    worker_reply = staticmethod(lambda _channel: [])

    def eval(self, script, _numkeys, key, *args):
        if script == quota.CHARGE_SCRIPT:
            cost, limit, window = (int(a) for a in args)
            used = int(self.get(key) or 0)
            ttl = self.ttl(key)
            if used + cost > limit:
                return [0, used, ttl if ttl >= 0 else window]
            self.values[key] = str(used + cost)
            if ttl < 0:
                self.expiry[key] = time.time() + window
                ttl = window
            return [1, used + cost, ttl]
        if script == quota.REFUND_SCRIPT:
            if not self._live(key):
                return 0
            left = int(self.values[key]) - int(args[0])
            if left <= 0:
                self.delete(key)
            else:
                self.values[key] = str(left)
            return left
        if script == quota.RELEASE_SCRIPT:
            if self.get(key) == args[0]:
                self.delete(key)
                return 1
            return 0
        if script == quota.SWAP_SCRIPT:
            if self.get(key) == args[0]:
                self.set(key, args[1], ex=int(args[2]))
                return 1
            return 0
        raise AssertionError("unexpected script")


@pytest.fixture
def fake_redis(monkeypatch):
    from services.engine import render_orchestrator
    fake = FakeRedis()
    # A live worker heartbeat: admission checks for one before charging.
    fake.set(render_orchestrator.RENDER_WORKER_HEARTBEAT_KEY, str(int(time.time())))
    monkeypatch.setattr(render_orchestrator, "r", fake)
    return fake


def _worker_log(payload) -> str:
    """What the CadQuery runner prints: it echoes the visitor's parameters."""
    return "".join(
        f"[{p}] Loading parameters: {json.dumps(payload['params'])}\n[{p}] Exported {p}.stl\n"
        for p in payload["parts"]
    )


class FakePubSub:
    """The worker's side of one part: answers a subscription with ``reply(part)``."""

    def __init__(self, fake):
        self.fake = fake
        self.pending: list = []

    def subscribe(self, channel):
        from services.engine.render_contract import RENDER_FINAL_CHANNEL_SUFFIX
        if channel.endswith(f":{RENDER_FINAL_CHANNEL_SUFFIX}"):
            for event in self.fake.worker_reply(channel):
                self.pending.append({"channel": channel, "data": json.dumps(event)})

    def get_message(self, timeout=0):
        return self.pending.pop(0) if self.pending else None

    def close(self):
        pass


@pytest.fixture
def renders(monkeypatch):
    """Stand in for the worker round trip; record every render that ran."""
    calls = []

    def fake_sync(_data, payload, engine, *_args, status=None, on_tick=None, deadline=None):
        calls.append(engine)
        if on_tick:
            on_tick()
        if status is not None:
            status.completed_parts = len(payload["parts"])
            status.finished = True
        return ([{"type": p, "url": f"/static/{p}.stl"} for p in payload["parts"]],
                _worker_log(payload), (0, len(payload["parts"])))

    def fake_stream(_data, payload, engine, *_args, status=None, on_tick=None, deadline=None):
        calls.append(engine)
        if on_tick:
            on_tick()
        if status is not None:
            status.completed_parts = len(payload["parts"])
            status.finished = True
        yield f"data: {json.dumps({'event': 'output', 'line': _worker_log(payload)})}\n\n"
        yield f"data: {json.dumps({'event': 'complete', 'parts': payload['parts']})}\n\n"

    monkeypatch.setattr("routes.engine.render.render_parts_sync", fake_sync)
    monkeypatch.setattr("routes.engine.render.render_parts_stream", fake_stream)
    return calls


@pytest.fixture
def cache(monkeypatch):
    """Parameter values the render cache holds; everything else is a miss."""
    hits: set = set()

    def fake_check(payload, part, export_format):
        if payload.get("ignore_cache"):
            return None
        return {"size_bytes": 1} if payload["params"].get("size") in hits else None

    monkeypatch.setattr("services.engine.render_orchestrator._check_cache", fake_check)
    return hits


@pytest.fixture
def app(tmp_path, user_projects_dir, fake_redis, renders, cache):
    from config import Config
    _cartridge(Path(Config.PROJECTS_DIR), "cq-commons")
    _cartridge(Path(Config.PROJECTS_DIR), "graph-commons", engine="graph")
    _cartridge(Path(Config.PROJECTS_DIR), "cq-two-parts", parts=("lid", "base"))
    _cartridge(Path(user_projects_dir), "cq-fork", meta=FORK_META)

    # Enabled BEFORE the app is built: flask-limiter's init_app skips its
    # storage entirely for a disabled limiter (conftest disables it).
    from extensions import limiter
    limiter.enabled = True

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    limiter.reset()
    yield flask_app
    limiter.reset()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def as_tier(monkeypatch):
    def seat(tier):
        # The render module's own binding: both the hourly bucket and the
        # gating tier read it, as in production.
        monkeypatch.setattr("routes.engine.render.resolve_tier", lambda *_a, **_k: tier)
    return seat


def _slots(fake):
    return {k: v for k, v in fake.values.items() if k.startswith(quota.SLOT_KEY_PREFIX)}


def _render(client, size, *, project="cq-commons", ip="198.51.100.7", fmt="stl", stream=False,
            text=None, **extra):
    parameters = {"size": size} if text is None else {"size": size, "text": text}
    body = {"project": project, "mode": "body", "parameters": parameters, "export_format": fmt, **extra}
    path = "/api/render-stream" if stream else "/api/render"
    return client.post(path, json=body, headers={"CF-Connecting-IP": ip})


# ──────────────────────────────────────────────
# The tier matrix
# ──────────────────────────────────────────────

class TestTierMatrix:
    @pytest.mark.parametrize("tier,expected", [("guest", 3), ("essentials", 10), ("pro", -1), ("premium", -1)])
    def test_daily_quota_per_tier(self, tier, expected):
        assert get_tier_limits(tier)[quota.QUOTA_KEY] == expected

    @pytest.mark.parametrize("tier", ["guest", "essentials"])
    def test_free_tiers_still_lack_the_engines_outright(self, tier):
        # The quota opens Commons re-renders only; the flags stay off, so a
        # fork, an import or a private cartridge still answers 403.
        assert not check_feature(tier, "cadquery_engine")
        assert not check_feature(tier, "graph_engine")

    @pytest.mark.parametrize("tier", ["guest", "essentials"])
    @pytest.mark.parametrize("feature", [
        "premium_export", "print_dispatch", "thickness_analysis", "overhang_analysis",
        "github_import", "github_private", "github_editor", "ai_code_editor", "animation",
    ])
    def test_what_stays_pro(self, tier, feature):
        assert not check_feature(tier, feature)

    @pytest.mark.parametrize("tier", ["guest", "essentials"])
    def test_step_export_stays_pro(self, tier):
        assert "step" not in get_tier_limits(tier)["export_formats"]


# ──────────────────────────────────────────────
# Engine resolution
# ──────────────────────────────────────────────

class TestEngineResolution:
    def _payload(self, slug):
        from services.engine.render_orchestrator import extract_render_payload
        return extract_render_payload({"project": slug, "mode": "body", "parameters": {}, "export_format": "stl"})

    def test_commons_cadquery_is_metered_for_guest(self, app):
        from services.engine.render_orchestrator import resolve_engine_config
        payload = self._payload("cq-commons")
        engine, _p, fmt, err = resolve_engine_config({"mode": "body"}, payload, "guest", allow_commons_quota=True)
        assert (engine, fmt, err) == ("cadquery", "stl", None)
        assert payload[quota.METERED_FLAG] is True

    def test_other_callers_keep_the_403(self, app):
        # HEAD renders and animations do not opt in.
        from services.engine.render_orchestrator import resolve_engine_config
        payload = self._payload("cq-commons")
        _e, _p, _f, err = resolve_engine_config({"mode": "body"}, payload, "guest")
        assert err == ("CadQuery engine is not available for your tier.", 403)
        assert quota.METERED_FLAG not in payload

    def test_fork_is_not_commons(self, app):
        from services.engine.render_orchestrator import resolve_engine_config
        payload = self._payload("cq-fork")
        _e, _p, _f, err = resolve_engine_config({"mode": "body"}, payload, "essentials", allow_commons_quota=True)
        assert err == ("CadQuery engine is not available for your tier.", 403)

    def test_pro_is_never_metered(self, app):
        from services.engine.render_orchestrator import resolve_engine_config
        payload = self._payload("cq-commons")
        _e, _p, _f, err = resolve_engine_config({"mode": "body"}, payload, "pro", allow_commons_quota=True)
        assert err is None
        assert quota.METERED_FLAG not in payload

    def test_zero_quota_keeps_the_403(self, app, monkeypatch):
        from services.engine.render_orchestrator import resolve_engine_config
        monkeypatch.setattr(quota, "quota_limit", lambda _tier: 0)
        payload = self._payload("cq-commons")
        _e, _p, _f, err = resolve_engine_config({"mode": "body"}, payload, "guest", allow_commons_quota=True)
        assert err[1] == 403


# ──────────────────────────────────────────────
# The quota through the routes
# ──────────────────────────────────────────────

class TestQuota:
    def test_guest_gets_three_then_a_clear_429(self, client, renders):
        for size in (11, 12, 13):
            res = _render(client, size)
            assert res.status_code == 200, res.get_json()
        assert res.headers["X-Commons-Render-Limit"] == "3"
        assert res.headers["X-Commons-Render-Remaining"] == "0"

        res = _render(client, 14)
        assert res.status_code == 429
        body = res.get_json()
        assert body["status"] == "error"
        assert body["error_code"] == quota.QUOTA_EXHAUSTED_CODE
        assert "3 free CadQuery re-renders" in body["error"]
        assert body["quota"]["limit"] == 3
        assert body["quota"]["remaining"] == 0
        assert body["quota"]["window"] == "day"
        assert body["quota"]["reset_at"].endswith("Z")
        assert 0 < body["retry_after_seconds"] <= 86400
        # flask-limiter re-renders Retry-After as max(ours, the route's own
        # window), truncating to whole seconds; the body is exact.
        assert int(res.headers["Retry-After"]) >= body["retry_after_seconds"] - 1
        assert body["tier"] == "guest"
        assert body["engine"] == "cadquery"
        assert renders == ["cadquery"] * 3

    def test_essentials_gets_ten(self, client, as_tier):
        as_tier("essentials")
        for size in range(20, 30):
            assert _render(client, size).status_code == 200
        res = _render(client, 30)
        assert res.status_code == 429
        assert res.get_json()["quota"]["limit"] == 10

    def test_graph_engine_is_metered_too(self, client):
        for size in (11, 12, 13):
            assert _render(client, size, project="graph-commons").status_code == 200
        res = _render(client, 14, project="graph-commons")
        assert res.status_code == 429
        assert res.get_json()["engine"] == "graph"

    def test_identities_have_their_own_buckets(self, client):
        for size in (11, 12, 13):
            assert _render(client, size, ip="198.51.100.1").status_code == 200
        assert _render(client, 14, ip="198.51.100.1").status_code == 429
        assert _render(client, 14, ip="198.51.100.2").status_code == 200

    def test_cache_hit_is_not_counted(self, client, cache, renders):
        cache.add(50)
        for _ in range(5):
            res = _render(client, 50)
            assert res.status_code == 200
            assert res.headers["X-Commons-Render-Cache"] == "HIT"
        # All three cold renders are still there.
        for size in (11, 12, 13):
            assert _render(client, size).status_code == 200
        assert _render(client, 14).status_code == 429
        # And a cached result is still served once the quota is spent.
        assert _render(client, 50).status_code == 200

    def test_forced_rerender_bypasses_the_cache_and_counts(self, client, cache):
        cache.add(50)
        res = _render(client, 50, ignore_cache=True)
        assert res.status_code == 200
        assert res.headers["X-Commons-Render-Remaining"] == "2"

    def test_quota_resets_after_the_window(self, client, monkeypatch):
        monkeypatch.setattr(quota, "QUOTA_WINDOW_SECONDS", 1)
        for size in (11, 12, 13):
            assert _render(client, size).status_code == 200
        assert _render(client, 14).status_code == 429
        time.sleep(1.2)
        res = _render(client, 15)
        assert res.status_code == 200
        assert res.headers["X-Commons-Render-Remaining"] == "2"

    def test_stream_route_is_metered_and_releases_the_lease(self, client, fake_redis):
        for size in (11, 12, 13):
            res = _render(client, size, stream=True)
            assert res.status_code == 200
            res.get_data()  # drain the stream
            assert _slots(fake_redis) == {}
        res = _render(client, 14, stream=True)
        assert res.status_code == 429
        assert res.get_json()["error_code"] == quota.QUOTA_EXHAUSTED_CODE

    def test_pro_is_not_metered(self, client, as_tier):
        as_tier("pro")
        for size in range(11, 16):
            res = _render(client, size)
            assert res.status_code == 200
            assert "X-Commons-Render-Limit" not in res.headers

    def test_free_tiers_still_cannot_render_a_fork(self, client, as_tier):
        as_tier("essentials")
        res = _render(client, 11, project="cq-fork")
        assert res.status_code == 403

    def test_step_export_still_needs_pro(self, client, as_tier):
        as_tier("essentials")
        res = _render(client, 11, fmt="step")
        assert res.status_code == 403
        assert "requires Pro tier" in res.get_json()["error"]

    def test_not_enforced_when_rate_limiting_is_off(self, client):
        from extensions import limiter
        limiter.enabled = False
        for size in range(11, 16):
            assert _render(client, size).status_code == 200


# ──────────────────────────────────────────────
# Burst bounds
# ──────────────────────────────────────────────

class TestBurstBounds:
    def test_one_free_render_at_a_time(self, client, fake_redis):
        fake_redis.set(f"{quota.SLOT_KEY_PREFIX}0", "live:other:req-x")
        res = _render(client, 11)
        assert res.status_code == 503
        body = res.get_json()
        assert body["error_code"] == quota.BUSY_CODE
        assert body["retry_after_seconds"] == quota.BUSY_RETRY_AFTER_SECONDS
        assert int(res.headers["Retry-After"]) >= quota.BUSY_RETRY_AFTER_SECONDS - 1
        # Nothing was counted: once the slot frees, all three are there.
        fake_redis.delete(f"{quota.SLOT_KEY_PREFIX}0")
        for size in (11, 12, 13):
            assert _render(client, size).status_code == 200

    def test_lease_is_released_after_a_sync_render(self, client, fake_redis):
        assert _render(client, 11).status_code == 200
        assert _slots(fake_redis) == {}

    def test_lease_is_released_when_the_render_raises(self, client, fake_redis, monkeypatch):
        def boom(*_a, **_k):
            raise OSError("disk full")
        monkeypatch.setattr("routes.engine.render.render_parts_sync", boom)
        assert _render(client, 11).status_code == 500
        assert _slots(fake_redis) == {}
        # ...and the failure was refunded.
        assert fake_redis.get(f"{quota.QUOTA_KEY_PREFIX}ip:198.51.100.7") is None

    def test_hourly_ceiling_across_all_free_visitors(self, client, monkeypatch):
        monkeypatch.setenv(quota.GLOBAL_PARTS_ENV, "2")
        assert _render(client, 11, ip="203.0.113.1").status_code == 200
        assert _render(client, 11, ip="203.0.113.2").status_code == 200
        res = _render(client, 11, ip="203.0.113.3")
        assert res.status_code == 503
        assert res.get_json()["error_code"] == quota.CAPACITY_EXHAUSTED_CODE
        assert int(res.headers["Retry-After"]) > 0

    def test_slot_store_down_fails_closed(self, client, monkeypatch):
        def down():
            raise ConnectionError("redis down")
        monkeypatch.setattr(quota, "_redis", down)
        res = _render(client, 11)
        assert res.status_code == 503
        assert res.get_json()["error_code"] == quota.BUSY_CODE


def _part_done_reply(text_in_log: str):
    """The worker finishing a part, its log echoing a visitor-chosen string."""
    from services.engine.render_contract import RENDER_EVENT_PART_DONE, build_render_event

    def reply(channel):
        return [build_render_event(
            RENDER_EVENT_PART_DONE, part="body", type="body", url="/static/body.stl", size_bytes=1,
            log=f'[body] Loading parameters: {{"size": 11, "text": "{text_in_log}"}}\n'
                f"[body] ERROR: is just text the visitor typed\n[body] Exported body.stl\n",
        )]
    return reply


class TestSettlement:
    """Settled from the render loop's structured status, never from log text.

    Only infrastructure failures are refunded; abandoned work is stopped.
    """

    GUEST_KEY = f"{quota.QUOTA_KEY_PREFIX}ip:198.51.100.7"

    def _real_loops(self, monkeypatch):
        from services.engine import render_orchestrator as orch
        monkeypatch.setattr("routes.engine.render.render_parts_sync", orch.render_parts_sync)
        monkeypatch.setattr("routes.engine.render.render_parts_stream", orch.render_parts_stream)

    def test_a_successful_render_whose_log_says_error_stays_charged(self, client, fake_redis, monkeypatch):
        # The CadQuery runner prints the visitor's parameters, so a nameplate
        # whose text is "ERROR" puts that word in the log of a render that
        # succeeded. It must not be read as a failure (and refunded).
        self._real_loops(monkeypatch)
        fake_redis.worker_reply = _part_done_reply("ERROR")
        for size in (11, 12, 13):
            res = _render(client, size, text="ERROR")
            assert res.status_code == 200
            assert "ERROR" in res.get_json()["log"]
        assert fake_redis.get(self.GUEST_KEY) == "3"
        assert _render(client, 14, text="ERROR").status_code == 429

    def test_the_same_through_the_stream(self, client, fake_redis, monkeypatch):
        self._real_loops(monkeypatch)
        fake_redis.worker_reply = _part_done_reply("ERROR")
        for size in (11, 12, 13):
            res = _render(client, size, text="ERROR", stream=True)
            assert b"Render cancelled by user request" not in res.get_data()
        assert fake_redis.get(self.GUEST_KEY) == "3"
        assert _slots(fake_redis) == {}

    def test_worker_down_is_refused_before_charging(self, client, fake_redis):
        from services.engine import render_orchestrator
        fake_redis.delete(render_orchestrator.RENDER_WORKER_HEARTBEAT_KEY)
        res = _render(client, 11)
        assert res.status_code == 503
        assert res.get_json()["error_code"] == "render_worker_unavailable"
        assert fake_redis.get(self.GUEST_KEY) is None
        assert fake_redis.get(quota.GLOBAL_KEY) is None

    def test_a_script_error_is_not_refunded(self, client, fake_redis, monkeypatch):
        # A CadQuery exception may come from the visitor's own parameters.
        from services.engine.render_contract import RENDER_EVENT_ERROR, build_render_event
        self._real_loops(monkeypatch)
        fake_redis.worker_reply = lambda _c: [build_render_event(
            RENDER_EVENT_ERROR, part="body", error="StdFail_NotDone", message="StdFail_NotDone")]
        for size in (11, 12, 13):
            assert _render(client, size).status_code == 200
        assert fake_redis.get(self.GUEST_KEY) == "3"
        assert fake_redis.get(quota.GLOBAL_KEY) == "3"

    def test_a_timeout_is_not_refunded(self, client, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch
        self._real_loops(monkeypatch)
        monkeypatch.setattr(orch, "RENDER_PART_WAIT_TIMEOUT_SECONDS", 0)
        assert _render(client, 11).status_code == 200
        assert fake_redis.get(self.GUEST_KEY) == "1"
        assert _slots(fake_redis) == {}

    def test_worker_lost_mid_render_is_refunded(self, client, fake_redis, monkeypatch):
        def lost(*_a, status=None, **_k):
            status.worker_lost = True
            return None, "Render worker unavailable or not healthy", (0, 1)
        monkeypatch.setattr("routes.engine.render.render_parts_sync", lost)
        assert _render(client, 11).status_code == 503
        assert fake_redis.get(self.GUEST_KEY) is None

    def test_worker_lost_in_the_stream_is_refunded(self, client, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch
        self._real_loops(monkeypatch)
        # Admission saw a live worker; it disappears before the part is queued.
        monkeypatch.setattr(orch, "is_render_worker_available", iter([True] + [False] * 10).__next__)
        res = _render(client, 11, stream=True)
        assert b"Render worker unavailable" in res.get_data()
        assert fake_redis.get(self.GUEST_KEY) is None

    def test_an_exception_is_refunded(self, client, fake_redis, monkeypatch):
        def boom(*_a, **_k):
            raise OSError("disk full")
        monkeypatch.setattr("routes.engine.render.render_parts_sync", boom)
        assert _render(client, 11).status_code == 500
        assert fake_redis.get(self.GUEST_KEY) is None
        assert _slots(fake_redis) == {}

    def test_abandoned_stream_cancels_its_jobs_and_drains_the_lease(self, client, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch

        def long_render(_data, payload, *_a, status=None, on_tick=None, deadline=None):
            # The worker is rendering part 1 and part 2 is queued behind it.
            fake_redis.sets.setdefault(orch.ACTIVE_RENDER_JOBS_KEY, set()).add("job-1")
            fake_redis.set(f"{orch.ACTIVE_RENDER_META_PREFIX}job-1",
                           json.dumps({"request_id": payload["request_id"], "part": "body"}), ex=600)
            fake_redis.rpush(orch.RENDER_QUEUE, json.dumps(
                {"job_id": "job-2", "request_id": payload["request_id"], "part": "lid"}))
            fake_redis.rpush(orch.RENDER_QUEUE, json.dumps(
                {"job_id": "someone-else", "request_id": "other", "part": "x"}))
            yield f"data: {json.dumps({'event': 'job', 'job_ids': ['job-1', 'job-2']})}\n\n"
            yield f"data: {json.dumps({'event': 'progress', 'progress': 10})}\n\n"
        monkeypatch.setattr("routes.engine.render.render_parts_stream", long_render)

        res = _render(client, 11, stream=True, request_id="req-abandoned")
        assert res.status_code == 200
        body = iter(res.response)
        next(body)  # the first event reaches the visitor...
        res.close()  # ...who goes away before `complete`

        # The real cancel sweep ran: the queued part is gone, the other
        # visitor's job is untouched, the running part was told to stop, and
        # parts not yet queued will not be.
        queued = [json.loads(t)["job_id"] for t in fake_redis.lists[orch.RENDER_QUEUE]]
        assert queued == ["someone-else"]
        assert fake_redis.get(f"{orch.CANCEL_JOB_PREFIX}job-1") == "1"
        assert orch.is_request_cancelled("req-abandoned")
        # Not refunded: the visitor walked away, the server did not fail.
        assert fake_redis.get(self.GUEST_KEY) == "1"
        # The worker is still stopping, so the lease drains instead of freeing.
        [(key, value)] = _slots(fake_redis).items()
        assert value.startswith("drain:") and value.endswith(":req-abandoned")
        assert 0 < fake_redis.ttl(key) <= orch.ACTIVE_JOB_META_TTL

        monkeypatch.setattr("routes.engine.render.render_parts_stream",
                            lambda *_a, **_k: iter([f"data: {json.dumps({'event': 'complete', 'parts': []})}\n\n"]))
        busy = _render(client, 12, ip="198.51.100.8")
        assert busy.status_code == 503 and busy.get_json()["error_code"] == quota.BUSY_CODE
        # Once the worker lets go of the job, the next free render takes the lease over.
        fake_redis.sets[orch.ACTIVE_RENDER_JOBS_KEY].clear()
        assert _render(client, 12, ip="198.51.100.8").status_code == 200

    def test_a_never_iterated_stream_does_not_leak_the_lease(self, client, fake_redis):
        res = _render(client, 11, stream=True)
        assert res.status_code == 200
        res.close()  # closed without reading a byte
        assert _slots(fake_redis) == {}

    def test_global_budget_is_charged_per_computed_part(self, client, fake_redis, monkeypatch):
        monkeypatch.setenv(quota.GLOBAL_PARTS_ENV, "3")
        assert _render(client, 11, project="cq-two-parts", ip="203.0.113.1").status_code == 200
        assert fake_redis.get(quota.GLOBAL_KEY) == "2"
        res = _render(client, 11, project="cq-two-parts", ip="203.0.113.2")
        assert res.status_code == 503
        assert res.get_json()["error_code"] == quota.CAPACITY_EXHAUSTED_CODE
        assert _render(client, 11, ip="203.0.113.3").status_code == 200
        assert fake_redis.get(quota.GLOBAL_KEY) == "3"

    def test_global_units_are_given_back_when_the_identity_charge_throws(self, client, fake_redis, monkeypatch):
        real_charge = quota._charge

        def flaky(key, *args):
            if key.startswith(quota.QUOTA_KEY_PREFIX):
                raise ConnectionError("redis blip")
            return real_charge(key, *args)
        monkeypatch.setattr(quota, "_charge", flaky)
        res = _render(client, 11)
        assert res.status_code == 503 and res.get_json()["error_code"] == quota.BUSY_CODE
        assert fake_redis.get(quota.GLOBAL_KEY) is None
        assert _slots(fake_redis) == {}


class TestExceptionsAndRequestIds:
    GUEST_KEY = f"{quota.QUOTA_KEY_PREFIX}ip:198.51.100.7"

    def test_gunicorns_timeout_is_not_refunded(self, client, fake_redis, monkeypatch):
        def killed(*_a, **_k):
            raise SystemExit(1)  # what gunicorn raises in a worker past --timeout
        monkeypatch.setattr("routes.engine.render.render_parts_sync", killed)
        with pytest.raises(SystemExit):
            _render(client, 11)
        assert fake_redis.get(self.GUEST_KEY) == "1"
        assert _slots(fake_redis) == {}

    def test_a_redis_error_is_refunded(self, client, fake_redis, monkeypatch):
        import redis

        def blip(*_a, **_k):
            raise redis.ConnectionError("render redis went away")
        monkeypatch.setattr("routes.engine.render.render_parts_sync", blip)
        assert _render(client, 11).status_code == 500
        assert fake_redis.get(self.GUEST_KEY) is None

    def test_a_bug_is_not_refunded(self, client, fake_redis, monkeypatch):
        def bug(*_a, **_k):
            raise KeyError("parts")
        monkeypatch.setattr("routes.engine.render.render_parts_sync", bug)
        assert _render(client, 11).status_code == 500
        assert fake_redis.get(self.GUEST_KEY) == "1"

    @pytest.mark.parametrize("raw", [5, ["x"], {"a": 1}, "", "has space", "x" * 129, "semi;colon"])
    def test_an_unusable_request_id_is_replaced(self, app, raw):
        from services.engine.render_orchestrator import extract_render_payload
        payload = extract_render_payload({"project": "cq-commons", "mode": "body", "parameters": {},
                                          "export_format": "stl", "request_id": raw})
        assert isinstance(payload["request_id"], str) and payload["request_id"] != raw
        assert len(payload["request_id"]) == 36  # a server-minted UUID

    def test_a_good_request_id_is_kept(self, app):
        from services.engine.render_orchestrator import extract_render_payload
        payload = extract_render_payload({"project": "cq-commons", "mode": "body", "parameters": {},
                                          "export_format": "stl", "request_id": "req_A-1"})
        assert payload["request_id"] == "req_A-1"

    def test_an_abandoned_render_with_a_numeric_request_id_is_still_stopped(self, client, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch

        def long_render(_data, payload, *_a, status=None, on_tick=None, deadline=None):
            fake_redis.sets.setdefault(orch.ACTIVE_RENDER_JOBS_KEY, set()).add("job-5")
            fake_redis.set(f"{orch.ACTIVE_RENDER_META_PREFIX}job-5",
                           json.dumps({"request_id": payload["request_id"], "part": "body"}), ex=600)
            yield f"data: {json.dumps({'event': 'job', 'job_ids': ['job-5']})}\n\n"
            yield f"data: {json.dumps({'event': 'progress', 'progress': 10})}\n\n"
        monkeypatch.setattr("routes.engine.render.render_parts_stream", long_render)

        res = _render(client, 11, stream=True, request_id=5)
        next(iter(res.response))
        res.close()
        assert fake_redis.get(f"{orch.CANCEL_JOB_PREFIX}job-5") == "1"
        [(_key, value)] = _slots(fake_redis).items()
        assert value.startswith("drain:")


class TestLiveLease:
    def test_live_lease_is_short_and_refreshed_by_the_wait_loop(self, app, fake_redis):
        from services.engine.render_orchestrator import extract_render_payload
        with app.test_request_context():
            payload = extract_render_payload({"project": "cq-commons", "mode": "body",
                                              "parameters": {}, "export_format": "stl"})
            key, lease = quota._acquire_slot(payload)
        assert 0 < fake_redis.ttl(key) <= quota.LIVE_LEASE_SECONDS
        grant = quota.MeteredRender(slot_key=key, lease=lease)
        fake_redis.expiry[key] = time.time() + 5  # nearly expired
        grant._last_refresh = 0
        grant.refresh()
        assert fake_redis.ttl(key) > 50
        # Throttled: a refresh right after does nothing.
        fake_redis.expiry[key] = time.time() + 5
        grant.refresh()
        assert fake_redis.ttl(key) <= 5

    def test_a_dead_owners_lease_frees_itself(self, client, fake_redis):
        # The owner process died mid-render: nothing refreshes its live lease.
        fake_redis.set(f"{quota.SLOT_KEY_PREFIX}0", "live:dead:req-dead", ex=quota.LIVE_LEASE_SECONDS)
        assert _render(client, 11).status_code == 503
        fake_redis.expiry[f"{quota.SLOT_KEY_PREFIX}0"] = time.time() - 1
        assert _render(client, 11).status_code == 200

    def test_metered_waits_end_before_gunicorn_would_kill_the_worker(self):
        assert quota.METERED_MAX_WAIT_SECONDS < 300  # apps/api/Dockerfile: gunicorn --timeout 300


class TestMeteredTimeoutStopsTheWorker:
    def test_sync_timeout_cancels_the_job_and_stops_queueing(self, app, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch

        class SilentPubSub:
            def subscribe(self, *_a):
                pass

            def get_message(self, timeout=0):
                return None

            def close(self):
                pass

        fake_redis.pubsub = lambda **_k: SilentPubSub()
        monkeypatch.setattr(orch, "RENDER_PART_WAIT_TIMEOUT_SECONDS", 0)
        cancelled = []
        monkeypatch.setattr(orch, "cancel_render_jobs", lambda ids: cancelled.extend(ids) or list(ids))

        payload = orch.extract_render_payload({"project": "cq-two-parts", "mode": "body",
                                               "parameters": {}, "export_format": "stl"})
        payload[quota.METERED_FLAG] = True
        parts, log, _stats = orch.render_parts_sync({}, payload, "cadquery", payload["scad_path"], "stl", "guest")
        assert parts == []
        assert "timed out" in log
        queued = fake_redis.lists.get(orch.RENDER_QUEUE, [])
        assert len(queued) == 1, "the second part must not be queued after a timeout"
        assert cancelled == [json.loads(queued[0])["job_id"]]

    def test_the_metered_deadline_bounds_every_wait(self, app, fake_redis, monkeypatch):
        from services.engine import render_orchestrator as orch
        cancelled, ticks = [], []
        monkeypatch.setattr(orch, "cancel_render_jobs", lambda ids: cancelled.extend(ids) or list(ids))
        payload = orch.extract_render_payload({"project": "cq-two-parts", "mode": "body",
                                               "parameters": {}, "export_format": "stl"})
        payload[quota.METERED_FLAG] = True
        queue = lambda: fake_redis.lists.get(orch.RENDER_QUEUE, [])

        # Per-part wait is the normal 120 s; the request deadline arrives
        # while the first part is on the worker: that part is cancelled and
        # the second is never queued.
        status = orch.RenderStatus()
        orch.render_parts_sync({}, payload, "cadquery", payload["scad_path"], "stl", "guest",
                               status=status, on_tick=lambda: ticks.append(1), deadline=time.time() + 0.3)
        assert status.timed_out and not status.finished
        assert len(queue()) == 1 and cancelled == [json.loads(queue()[0])["job_id"]] and ticks

        stream_status = orch.RenderStatus()
        events = list(orch.render_parts_stream({}, payload, "cadquery", payload["scad_path"], "stl",
                                               status=stream_status, deadline=time.time() + 0.3))
        assert stream_status.timed_out and not stream_status.finished
        assert len(queue()) == 2 and len(cancelled) == 2
        assert '"event": "complete"' in events[-1]

    def test_nothing_is_queued_once_the_deadline_has_passed(self, app, fake_redis):
        from services.engine import render_orchestrator as orch
        payload = orch.extract_render_payload({"project": "cq-two-parts", "mode": "body",
                                               "parameters": {}, "export_format": "stl"})
        payload[quota.METERED_FLAG] = True
        status = orch.RenderStatus()
        orch.render_parts_sync({}, payload, "cadquery", payload["scad_path"], "stl", "guest",
                               status=status, deadline=time.time() - 1)
        stream_status = orch.RenderStatus()
        list(orch.render_parts_stream({}, payload, "cadquery", payload["scad_path"], "stl",
                                      status=stream_status, deadline=time.time() - 1))
        assert status.timed_out and stream_status.timed_out
        assert fake_redis.lists.get(orch.RENDER_QUEUE, []) == []

    def test_the_deadline_counts_from_when_the_request_arrived(self, app):
        from flask import g
        with app.test_request_context("/api/render", method="POST"):
            app.preprocess_request()  # runs the request-id middleware
            assert abs(g.request_started_at - time.time()) < 5
            g.request_started_at = time.time() - 100
            grant = quota.MeteredRender()
            assert abs(grant.deadline - (g.request_started_at + quota.METERED_MAX_WAIT_SECONDS)) < 1


class TestClientAddress:
    def test_cloudflare_address_keys_every_anonymous_bucket(self, app):
        from extensions import tiered_rate_key
        from routes.engine.render import _rate_limit_key
        with app.test_request_context(headers={"CF-Connecting-IP": "203.0.113.9"}):
            assert tiered_rate_key() == "ip:203.0.113.9"
            assert _rate_limit_key() == "ip:203.0.113.9"
            assert quota.quota_identity() == "ip:203.0.113.9"

    def test_ipv6_is_keyed_by_its_64(self, app):
        from utils.client_ip import client_ip
        with app.test_request_context(headers={"CF-Connecting-IP": "2001:db8:1:2:aaaa::1"}):
            assert client_ip() == "2001:db8:1:2::/64"

    def test_a_non_address_header_is_ignored(self, app):
        from utils.client_ip import client_ip
        with app.test_request_context(headers={"CF-Connecting-IP": "not-an-ip"},
                                      environ_base={"REMOTE_ADDR": "10.0.0.5"}):
            assert client_ip() == "10.0.0.5"

    def test_guests_no_longer_share_the_hourly_render_bucket(self, client, cache):
        cache.add(50)  # cache hits: only the hourly bucket is involved
        for _ in range(10):
            assert _render(client, 50, ip="198.51.100.20").status_code == 200
        limited = _render(client, 50, ip="198.51.100.20")
        assert limited.status_code == 429
        assert (limited.get_json(silent=True) or {}).get("error_code") != quota.QUOTA_EXHAUSTED_CODE
        assert _render(client, 50, ip="198.51.100.21").status_code == 200


class TestCommonsCartridge:
    def test_private_flag_is_not_commons(self, app, monkeypatch):
        from manifest import get_manifest
        manifest = get_manifest("cq-commons")
        assert quota.is_commons_cartridge(manifest)
        monkeypatch.setattr("services.core.project_access.is_private_project",
                            lambda slug, _m=None: slug == "cq-commons")
        assert not quota.is_commons_cartridge(manifest)

    def test_private_root_is_not_commons(self, app, tmp_path):
        from config import Config
        from manifest import ProjectManifest
        path = _cartridge(Path(Config.PRIVATE_PROJECTS_DIR), "client-part")
        manifest = ProjectManifest(_manifest("client-part"), path)
        assert not quota.is_commons_cartridge(manifest)

    def test_manifest_without_a_directory_is_not_commons(self):
        assert not quota.is_commons_cartridge(object())

    def test_commons_root_shared_with_the_user_root_is_not_commons(self, app, monkeypatch):
        from config import Config
        from manifest import get_manifest
        manifest = get_manifest("cq-commons")
        assert quota.is_commons_cartridge(manifest)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", Config.PROJECTS_DIR)
        assert not quota.is_commons_cartridge(manifest)


@pytest.fixture(scope="module")
def real_redis():
    """A throwaway redis-server, where one is installed (skipped otherwise)."""
    import shutil
    import socket
    import subprocess

    binary = shutil.which("redis-server")
    if binary is None:
        pytest.skip("redis-server not installed")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    proc = subprocess.Popen(
        [binary, "--port", str(port), "--save", "", "--appendonly", "no", "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    import redis
    client = redis.Redis(host="127.0.0.1", port=port, decode_responses=True)
    for _ in range(50):
        try:
            client.ping()
            break
        except redis.ConnectionError:
            time.sleep(0.1)
    else:  # pragma: no cover - environment problem
        proc.kill()
        pytest.skip("redis-server did not start")
    yield client
    proc.terminate()
    proc.wait(timeout=10)


class TestLuaScriptsOnRealRedis:
    """The Lua the module sends, against real Redis, matched step for step by FakeRedis."""

    def _both(self, real, fake, script, key, *args):
        got = real.eval(script, 1, key, *args)
        expected = fake.eval(script, 1, key, *(str(a) for a in args))
        assert [int(x) for x in got] == [int(x) for x in expected] if isinstance(got, list) else int(got) == int(expected)
        return got

    def test_charge_and_refund(self, real_redis):
        fake, key = FakeRedis(), "t:quota"
        real_redis.delete(key)
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 1, 2, 100)[:2] == [1, 1]
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 1, 2, 100)[:2] == [1, 2]
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 1, 2, 100)[:2] == [0, 2]
        assert 0 < real_redis.ttl(key) <= 100
        assert int(self._both(real_redis, fake, quota.REFUND_SCRIPT, key, 1)) == 1
        assert int(self._both(real_redis, fake, quota.REFUND_SCRIPT, key, 1)) == 0
        assert real_redis.exists(key) == 0
        # A refund never creates a counter.
        assert int(self._both(real_redis, fake, quota.REFUND_SCRIPT, key, 1)) == 0
        assert real_redis.exists(key) == 0

    def test_charge_by_cost(self, real_redis):
        fake, key = FakeRedis(), "t:global"
        real_redis.delete(key)
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 2, 3, 100)[:2] == [1, 2]
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 2, 3, 100)[:2] == [0, 2]
        assert self._both(real_redis, fake, quota.CHARGE_SCRIPT, key, 1, 3, 100)[:2] == [1, 3]

    def test_release_and_swap_only_their_own_lease(self, real_redis):
        fake, key = FakeRedis(), "t:slot"
        for client in (real_redis, fake):
            client.set(key, "live:a:r1", ex=100)
        assert int(self._both(real_redis, fake, quota.RELEASE_SCRIPT, key, "live:b:r2")) == 0
        assert int(self._both(real_redis, fake, quota.SWAP_SCRIPT, key, "live:a:r1", "drain:a:r1", 50)) == 1
        assert real_redis.get(key) == "drain:a:r1" and 0 < real_redis.ttl(key) <= 50
        assert int(self._both(real_redis, fake, quota.SWAP_SCRIPT, key, "live:a:r1", "x", 50)) == 0
        assert int(self._both(real_redis, fake, quota.RELEASE_SCRIPT, key, "drain:a:r1")) == 1
        assert real_redis.exists(key) == 0
