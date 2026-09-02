"""`yantra_render_active_jobs` tells the truth about what is running.

The worker `sadd`s a job id at start and `srem`s it at finish, both in code that
only runs when the worker reaches its `finally`. A pod roll, an OOM kill or a
node eviction never does, so the id stays in a set with no expiry and nothing
left to remove it. `/api/health` then reports `active jobs 1` against `queue
depth 0` — observed in production across five samples and two rollouts on
2026-09-02, the count surviving the very restarts that should have cleared it.

The fix is a lease, and these tests pin both halves of it:

  1. `yantra_render_job_meta:<job_id>` is read as the job's lease. A member
     whose lease is gone — or stamped longer ago than any real render can run —
     is dropped by the read paths that report the count.
  2. The worker renews the lease of every job it is actually holding, and
     reconciles the whole set at startup so a rollout's orphans are gone
     immediately rather than one lease later.

And one non-regression: cancelling is NOT a reporting path. A caller holding a
`job_id` holds a capability, so `cancel_render_jobs` still acts on an id whose
lease this process cannot read (pinned by
tests/unit/test_render_cancel_scoped.py; re-pinned here against the pruning).

The fake Redis follows the one in tests/unit/test_render_cancel_scoped.py,
extended with the TTL bookkeeping a lease needs.
"""
import importlib.util
import json
import time
from pathlib import Path

import pytest

WORKER_PATH = Path(__file__).resolve().parents[3] / "worker" / "render_worker.py"


class FakeRedis:
    """In-memory Redis with enough TTL bookkeeping to model a lease.

    `expires` records the TTL each key was last written or renewed with, so a
    test can assert a lease was *renewed* rather than merely still present.
    """

    def __init__(self):
        self.strings: dict[str, str] = {}
        self.expires: dict[str, int | None] = {}
        self.lists: dict[str, list[str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.published: list[tuple[str, str]] = []
        self.fail_on: set[str] = set()

    def _guard(self, op):
        if op in self.fail_on:
            raise ConnectionError(f"fake redis: {op} unavailable")

    # strings
    def get(self, key):
        self._guard("get")
        return self.strings.get(key)

    def set(self, key, value, ex=None):
        self._guard("set")
        self.strings[key] = value
        self.expires[key] = ex

    def delete(self, key):
        self._guard("delete")
        self.strings.pop(key, None)
        self.expires.pop(key, None)

    def expire(self, key, ttl):
        self._guard("expire")
        if key not in self.strings:
            return False
        self.expires[key] = ttl
        return True

    # lists
    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def lrange(self, key, _start, _end):
        return list(self.lists.get(key, []))

    def lrem(self, key, _count, value):
        entries = self.lists.get(key, [])
        if value in entries:
            entries.remove(value)

    def llen(self, key):
        return len(self.lists.get(key, []))

    # sets
    def sadd(self, key, member):
        self.sets.setdefault(key, set()).add(member)

    def smembers(self, key):
        self._guard("smembers")
        return set(self.sets.get(key, set()))

    def scard(self, key):
        self._guard("scard")
        return len(self.sets.get(key, set()))

    def srem(self, key, member):
        self._guard("srem")
        self.sets.get(key, set()).discard(member)

    def publish(self, channel, message):
        self.published.append((channel, message))


@pytest.fixture
def orch(monkeypatch):
    from services.engine import render_orchestrator

    monkeypatch.setattr(render_orchestrator, "r", FakeRedis())
    return render_orchestrator


def activate(orch, job_id, *, started_at=None, lease=True, part="body",
             engine="openscad", request_id="req-1"):
    """Mark a job active exactly as render_worker.py::_set_active_job does.

    `lease=False` reproduces the production state: the id is in the set and the
    lease key has expired, because the worker that wrote it died mid-render.
    """
    orch.r.sadd(orch.ACTIVE_RENDER_JOBS_KEY, job_id)
    if lease:
        orch.r.set(
            f"{orch.ACTIVE_RENDER_META_PREFIX}{job_id}",
            json.dumps({
                "job_id": job_id, "part": part, "engine": engine,
                "request_id": request_id,
                "started_at": int(time.time() if started_at is None else started_at),
            }),
            ex=orch.ACTIVE_JOB_META_TTL,
        )


# ──────────────────────────────────────────────
# 1. The lease decides membership
# ──────────────────────────────────────────────

def test_an_orphan_without_a_lease_is_dropped(orch):
    """The production symptom, exactly: one member, no worker, no lease."""
    activate(orch, "orphan", lease=False)

    live, dropped = orch.prune_active_jobs()

    assert live == []
    assert dropped == ["orphan"]
    assert orch.r.smembers(orch.ACTIVE_RENDER_JOBS_KEY) == set()


def test_a_job_holding_a_fresh_lease_is_kept(orch):
    activate(orch, "running")

    live, dropped = orch.prune_active_jobs()

    assert live == ["running"]
    assert dropped == []


def test_a_long_render_inside_its_ceiling_is_not_pruned(orch):
    """A job at 290s of a 300s ceiling is doing its job, not haunting the set."""
    activate(orch, "slow", started_at=time.time() - 290)

    assert orch.active_job_ids() == ["slow"]


def test_a_lease_older_than_any_possible_render_is_dropped(orch):
    """Belt and braces for a lease that outlived its own TTL.

    A Redis restored from a snapshot, or a key written by an older worker with
    the smaller TTL, can present a lease that should have expired. The job's own
    ceiling still bounds it: nothing renders for longer than RENDER_TIMEOUT_S
    plus the conversion grace.
    """
    too_old = time.time() - (orch.RENDER_TIMEOUT_S + orch.ACTIVE_JOB_LEASE_GRACE_SECONDS + 1)
    activate(orch, "zombie", started_at=too_old)

    live, dropped = orch.prune_active_jobs()

    assert live == []
    assert dropped == ["zombie"]


def test_pruning_removes_the_cancel_key_too(orch):
    """A stale entry must not leave a cancel flag behind to hit a reused id."""
    activate(orch, "orphan", lease=False)
    orch.r.set(f"{orch.CANCEL_JOB_PREFIX}orphan", "1", ex=120)

    orch.prune_active_jobs()

    assert orch.r.get(f"{orch.CANCEL_JOB_PREFIX}orphan") is None


def test_the_lease_ttl_outlasts_a_render_plus_its_conversion(orch):
    """The lease must never expire under a job that is still legitimately running."""
    assert orch.ACTIVE_JOB_META_TTL > orch.RENDER_TIMEOUT_S
    assert orch.ACTIVE_JOB_META_TTL == (
        orch.RENDER_TIMEOUT_S + orch.ACTIVE_JOB_LEASE_GRACE_SECONDS
    )


# ──────────────────────────────────────────────
# 2. The health surface reports the truth
# ──────────────────────────────────────────────

def test_health_reports_zero_active_jobs_for_an_orphan(orch):
    """`active jobs 1, queue depth 0` was the bug; this is the assertion for it."""
    activate(orch, "orphan", lease=False)
    orch.r.set(orch.RENDER_WORKER_HEARTBEAT_KEY, str(int(time.time())))

    status = orch.get_render_worker_status()

    assert status["queue_depth"] == 0
    assert status["active_jobs"] == 0


def test_health_still_counts_real_work(orch):
    activate(orch, "job-a")
    activate(orch, "job-b")
    orch.r.rpush(orch.RENDER_QUEUE, json.dumps({"job_id": "job-c"}))
    orch.r.set(orch.RENDER_WORKER_HEARTBEAT_KEY, str(int(time.time())))

    status = orch.get_render_worker_status()

    assert status["active_jobs"] == 2
    assert status["queue_depth"] == 1


def test_an_unreachable_redis_reports_unknown_not_zero(orch):
    """"We could not tell" must never be published as "nothing is running"."""
    activate(orch, "job-a")
    orch.r.fail_on.add("scard")

    assert orch.active_job_count() is None
    assert orch.get_render_worker_status()["active_jobs"] is None


def test_a_read_failure_mid_prune_never_sweeps_live_work(orch):
    """A Redis blip must not be mistaken for an expired lease."""
    activate(orch, "running")
    orch.r.fail_on.add("get")

    live, dropped = orch.prune_active_jobs()

    assert live == ["running"]
    assert dropped == []


def test_pruning_never_raises_when_the_set_cannot_be_read(orch):
    orch.r.fail_on.add("smembers")

    assert orch.prune_active_jobs() == ([], [])
    assert orch.active_job_ids() == []


# ──────────────────────────────────────────────
# 3. Startup reconciliation
# ──────────────────────────────────────────────

def test_reconciliation_clears_what_a_dead_instance_left_behind(orch):
    """A rollout's orphans go immediately, not one lease later.

    Both entries are dropped — including the one whose lease is still valid.
    At worker start this process holds nothing and it is the only replica, so a
    live-looking lease can only belong to the instance it replaced.
    """
    activate(orch, "orphan-expired", lease=False)
    activate(orch, "orphan-fresh")

    dropped = orch.reconcile_active_jobs()

    assert sorted(dropped) == ["orphan-expired", "orphan-fresh"]
    assert orch.r.smembers(orch.ACTIVE_RENDER_JOBS_KEY) == set()
    assert orch.r.get(f"{orch.ACTIVE_RENDER_META_PREFIX}orphan-fresh") is None


def test_reconciliation_on_an_empty_set_is_a_no_op(orch):
    assert orch.reconcile_active_jobs() == []


def test_reconciliation_survives_an_unreachable_redis(orch):
    orch.r.fail_on.add("smembers")

    assert orch.reconcile_active_jobs() == []


# ──────────────────────────────────────────────
# 4. Cancelling is not a reporting path (non-regression)
# ──────────────────────────────────────────────

def test_cancel_by_job_id_still_reaches_a_job_with_no_readable_lease(orch):
    """Pinned by test_render_cancel_scoped.py; re-pinned against the pruning.

    A `job_id` is a capability the caller was handed on its own stream. An
    unreadable lease is not proof the render stopped — the worker polls
    `yantra_render_cancel_job:<job_id>` regardless — so cancel acts on what the
    caller named instead of quietly pruning it away.
    """
    activate(orch, "orphan", lease=False)

    assert orch.cancel_render_jobs(["orphan"]) == ["orphan"]
    assert orch.r.get(f"{orch.CANCEL_JOB_PREFIX}orphan") == "1"


# ──────────────────────────────────────────────
# 5. The worker end of the lease
# ──────────────────────────────────────────────

@pytest.fixture
def worker(monkeypatch, orch):
    """The real apps/worker/render_worker.py, wired to the same fake Redis."""
    spec = importlib.util.spec_from_file_location("render_worker_under_test", WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "r", orch.r)
    module._held_jobs.clear()
    yield module
    module._held_jobs.clear()


def test_setting_a_job_active_writes_a_lease_and_starts_renewing_it(worker, orch):
    worker._set_active_job("job-1", "body", "openscad", {"project_slug": "widget"})

    meta_key = f"{orch.ACTIVE_RENDER_META_PREFIX}job-1"
    assert "job-1" in orch.r.smembers(orch.ACTIVE_RENDER_JOBS_KEY)
    assert orch.r.expires[meta_key] == worker.ACTIVE_JOB_META_TTL
    assert worker._held_jobs == {"job-1"}


def test_the_heartbeat_renews_the_lease_of_a_held_job(worker, orch):
    worker._set_active_job("job-1", "body", "openscad", {})
    meta_key = f"{orch.ACTIVE_RENDER_META_PREFIX}job-1"
    orch.r.expires[meta_key] = 5  # as if most of the lease had elapsed

    worker._refresh_active_job_leases()

    assert orch.r.expires[meta_key] == worker.ACTIVE_JOB_META_TTL


def test_clearing_a_job_stops_the_renewal_before_touching_redis(worker, orch):
    """If the Redis calls fail, the entry must expire rather than be pinned open.

    Renewal is what keeps a lease alive, so it has to stop first — otherwise a
    failed `_clear_active_job` leaves the heartbeat thread holding open the very
    entry the cleanup was meant to remove.
    """
    worker._set_active_job("job-1", "body", "openscad", {})
    orch.r.fail_on.add("srem")

    with pytest.raises(ConnectionError):
        worker._clear_active_job("job-1")

    assert worker._held_jobs == set()
    worker._refresh_active_job_leases()  # no held job left to renew


def test_a_cleared_job_is_no_longer_renewed(worker, orch):
    worker._set_active_job("job-1", "body", "openscad", {})
    worker._clear_active_job("job-1")

    assert worker._held_jobs == set()
    assert orch.r.get(f"{orch.ACTIVE_RENDER_META_PREFIX}job-1") is None


def test_renewal_never_raises(worker, orch):
    worker._set_active_job("job-1", "body", "openscad", {})
    orch.r.fail_on.add("expire")

    worker._refresh_active_job_leases()  # must not propagate


def test_the_worker_reconciles_before_it_consumes_anything(worker, orch):
    """Startup reconciliation runs, and runs through the orchestrator's helper."""
    activate(orch, "left-behind", lease=False)

    assert worker._reconcile_active_jobs_on_start() == ["left-behind"]
    assert orch.r.smembers(orch.ACTIVE_RENDER_JOBS_KEY) == set()

    source = WORKER_PATH.read_text()
    run_worker = source.split("def run_worker():", 1)[1]
    reconcile_at = run_worker.index("_reconcile_active_jobs_on_start()")
    consume_at = run_worker.index("blpop")
    assert reconcile_at < consume_at, (
        "reconciliation must run before the worker consumes its first task"
    )


def test_startup_reconciliation_never_takes_the_worker_down(worker, orch):
    orch.r.fail_on.add("smembers")

    assert worker._reconcile_active_jobs_on_start() == []
