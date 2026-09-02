"""
Unit tests for the render worker's heartbeat and shutdown behaviour.

The worker moved out of the API pod into its own Deployment behind an HPA, and
three things had to change for that to be safe:

  * identity — every pod publishes its own key, so N replicas are countable and
    a wedged pod cannot hide behind a healthy sibling;
  * dual-write — the legacy fleet-wide key stays written so a pre-split API (a
    rollback) still sees a live worker;
  * a heartbeat on a timer rather than at the top of the job loop, so a render
    longer than the TTL does not read as a dead worker.

The module lives outside the api package, so it is imported by path.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

WORKER_PATH = (
    pathlib.Path(__file__).resolve().parents[3] / "worker" / "render_worker.py"
)


def _load_worker(monkeypatch, **env):
    """Import render_worker.py fresh with the given environment."""
    for key in ("RENDER_WORKER_ID", "HOSTNAME"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    spec = importlib.util.spec_from_file_location(
        f"_render_worker_under_test_{len(sys.modules)}", WORKER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def worker_available():
    if not WORKER_PATH.is_file():
        pytest.skip(f"render worker not present at {WORKER_PATH}")
    return True


class _FakePipeline:
    def __init__(self, sink):
        self._sink = sink
        self._staged = []

    def set(self, key, value, ex=None):
        self._staged.append((key, value, ex))
        return self

    def execute(self):
        self._sink.extend(self._staged)
        self._staged = []


class _FakeRedis:
    def __init__(self):
        self.writes = []
        self.deletes = []

    def pipeline(self):
        return _FakePipeline(self.writes)

    def delete(self, key):
        self.deletes.append(key)

    def value_of(self, key):
        return {k: v for k, v, _ in self.writes}[key]


def test_worker_id_prefers_explicit_env(worker_available, monkeypatch):
    """RENDER_WORKER_ID wins over HOSTNAME so identity is explicit."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-explicit", HOSTNAME="pod-implicit")
    assert module.WORKER_ID == "pod-explicit"
    assert module.WORKER_HEARTBEAT_KEY == "render_worker:heartbeat:pod-explicit"


def test_worker_id_falls_back_to_hostname(worker_available, monkeypatch):
    """Kubernetes sets HOSTNAME to the pod name; that is the documented key."""
    module = _load_worker(monkeypatch, HOSTNAME="yantra4d-render-worker-7d9-abc")
    assert module.WORKER_ID == "yantra4d-render-worker-7d9-abc"
    assert (
        module.WORKER_HEARTBEAT_KEY
        == "render_worker:heartbeat:yantra4d-render-worker-7d9-abc"
    )


def test_worker_id_never_empty_off_cluster(worker_available, monkeypatch):
    """Outside a cluster neither env var exists; the key must still be valid."""
    module = _load_worker(monkeypatch)
    assert module.WORKER_ID
    assert module.WORKER_HEARTBEAT_KEY != "render_worker:heartbeat:"


def test_heartbeat_writes_per_worker_and_legacy_keys(worker_available, monkeypatch):
    """Each beat writes the countable per-worker key and the compat global key."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    fake = _FakeRedis()
    monkeypatch.setattr(module, "r", fake)
    module._set_worker_state("busy", "job-42")

    module._publish_heartbeat()

    written = {key: (value, ttl) for key, value, ttl in fake.writes}
    assert set(written) == {
        "render_worker:heartbeat:pod-a",
        module.RENDER_WORKER_HEARTBEAT_KEY,
    }

    payload = json.loads(written["render_worker:heartbeat:pod-a"][0])
    assert payload["worker_id"] == "pod-a"
    assert payload["state"] == "busy"
    assert payload["job_id"] == "job-42"
    assert isinstance(payload["ts"], int)

    # The legacy key stays a bare timestamp — a pre-split API parses it with
    # int(float(...)) and would reject JSON.
    legacy_value = written[module.RENDER_WORKER_HEARTBEAT_KEY][0]
    assert int(legacy_value) == payload["ts"]

    # Both carry the TTL, so a dead worker expires rather than lingering.
    for _, ttl in written.values():
        assert ttl == module.RENDER_WORKER_HEARTBEAT_TTL_SECONDS


def test_heartbeat_interval_stays_inside_the_ttl(worker_available, monkeypatch):
    """A single missed tick must not be able to expire the key."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    assert module.HEARTBEAT_INTERVAL_SECONDS * 2 < module.RENDER_WORKER_HEARTBEAT_TTL_SECONDS


def test_shutdown_signal_requests_drain(worker_available, monkeypatch):
    """SIGTERM sets the drain flag rather than killing the job in hand."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    assert not module._shutdown.is_set()
    module._handle_shutdown(15, None)
    assert module._shutdown.is_set()


def test_drain_keeps_the_heartbeat_beating(worker_available, monkeypatch):
    """A draining worker is still alive and must keep publishing.

    If the beat stopped at SIGTERM the pod would disappear from the fleet for
    the whole grace period while it was still writing a render — and if it were
    the last worker, the API would see zero workers, fail readiness under
    RENDER_WORKER_REQUIRED and restart itself mid-render.
    """
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    fake = _FakeRedis()
    monkeypatch.setattr(module, "r", fake)

    module._handle_shutdown(15, None)

    assert module._shutdown.is_set(), "drain requested"
    assert not module._stop_beating.is_set(), "heartbeat must survive the drain"

    module._publish_heartbeat()
    payload = json.loads(fake.value_of(module.WORKER_HEARTBEAT_KEY))
    assert payload["state"] == "draining"


def test_drain_state_does_not_overwrite_an_in_flight_job(worker_available, monkeypatch):
    """A worker mid-render stays 'busy' through SIGTERM, job id intact."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    fake = _FakeRedis()
    monkeypatch.setattr(module, "r", fake)
    module._set_worker_state("busy", "job-7")

    module._handle_shutdown(15, None)
    module._publish_heartbeat()

    payload = json.loads(fake.value_of(module.WORKER_HEARTBEAT_KEY))
    assert payload["state"] == "busy"
    assert payload["job_id"] == "job-7"


def test_clear_heartbeat_drops_only_this_workers_key(worker_available, monkeypatch):
    """A clean exit retires this pod immediately, not the whole fleet's key."""
    module = _load_worker(monkeypatch, RENDER_WORKER_ID="pod-a")
    fake = _FakeRedis()
    monkeypatch.setattr(module, "r", fake)

    module._clear_heartbeat()

    assert fake.deletes == ["render_worker:heartbeat:pod-a"]
    assert module.RENDER_WORKER_HEARTBEAT_KEY not in fake.deletes
