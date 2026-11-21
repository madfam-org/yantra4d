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
                        "label": {"en": "Size"}}],
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
    """The three commands the free-render lease uses."""

    def __init__(self):
        self.values: dict[str, str] = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(quota, "_redis", lambda: fake)
    return fake


@pytest.fixture
def renders(monkeypatch):
    """Stand in for the worker round trip; record every render that ran."""
    calls = []

    def fake_sync(_data, payload, engine, *_args):
        calls.append(engine)
        return [{"type": p, "url": f"/static/{p}.stl"} for p in payload["parts"]], "ok", (0, len(payload["parts"]))

    def fake_stream(_data, payload, engine, *_args):
        calls.append(engine)
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


def _render(client, size, *, project="cq-commons", ip="198.51.100.7", fmt="stl", stream=False, **extra):
    body = {"project": project, "mode": "body", "parameters": {"size": size}, "export_format": fmt, **extra}
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
        monkeypatch.setattr(quota, "QUOTA_WINDOW", "1 second")
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
            assert fake_redis.values == {}
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
        fake_redis.values[f"{quota.SLOT_KEY_PREFIX}0"] = "someone-else"
        res = _render(client, 11)
        assert res.status_code == 503
        body = res.get_json()
        assert body["error_code"] == quota.BUSY_CODE
        assert body["retry_after_seconds"] == quota.BUSY_RETRY_AFTER_SECONDS
        assert int(res.headers["Retry-After"]) >= quota.BUSY_RETRY_AFTER_SECONDS - 1
        # Nothing was counted: once the slot frees, all three are there.
        fake_redis.values.clear()
        for size in (11, 12, 13):
            assert _render(client, size).status_code == 200

    def test_lease_is_released_after_a_sync_render(self, client, fake_redis):
        assert _render(client, 11).status_code == 200
        assert fake_redis.values == {}

    def test_lease_is_released_when_the_render_raises(self, client, fake_redis, monkeypatch):
        def boom(*_a, **_k):
            raise OSError("disk full")
        monkeypatch.setattr("routes.engine.render.render_parts_sync", boom)
        assert _render(client, 11).status_code == 500
        assert fake_redis.values == {}

    def test_lease_outlives_every_part(self, app):
        from services.engine.render_orchestrator import RENDER_STREAM_PART_TIMEOUT_SECONDS
        lease = quota._slot_lease_seconds({"parts": ["a", "b"]})
        assert lease >= 2 * RENDER_STREAM_PART_TIMEOUT_SECONDS

    def test_hourly_ceiling_across_all_free_visitors(self, client, monkeypatch):
        monkeypatch.setenv(quota.GLOBAL_HOURLY_ENV, "2")
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


class TestCommonsCartridge:
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
