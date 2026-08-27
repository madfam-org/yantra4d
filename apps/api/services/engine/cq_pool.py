"""
Warm CadQuery worker pool.

Every CadQuery render used to spawn a fresh ``python cq_runner.py``, and each of
those processes paid 1-3s importing cadquery (OCCT) before touching geometry. On
the forj storefront batch that fixed tax dominated the short renders.

This module keeps a small pool of persistent ``cq_runner.py --serve`` processes
that import the kernel once at startup and then serve jobs over JSON lines on
stdin/stdout. The security posture is unchanged: workers are still separate,
killable subprocesses running the same commons_sandbox validation path — see
``cq_runner.serve_forever``.

Design constraints this honours:

- **A wedged OCCT must not poison the pool.** Workers are recycled after
  ``YANTRA4D_CQ_WORKER_MAX_JOBS`` jobs, and killed and replaced on timeout,
  crash, or protocol violation. A worker is never returned to the pool in an
  unknown state.
- **Never fail closed on the pool itself.** If a worker cannot start (missing
  cadquery, constrained env, exhausted process limits), ``submit`` returns None
  and the caller falls back to the historical per-render spawn, logging a
  warning. A pool problem must never become a render failure.
- **Same timeout, same error surface.** Jobs are bounded by the same
  RENDER_TIMEOUT_S the subprocess path uses, and results are returned as
  ``(success, output)`` so the render contract is untouched.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable

from services.engine.render_engine import RENDER_TIMEOUT_S

logger = logging.getLogger(__name__)

RUNNER_SCRIPT = os.path.join(os.path.dirname(__file__), "cq_runner.py")

# Sentinel distinguishing "cancelled" from "timed out" as a readline outcome;
# None already means timeout and both must lead to different error text.
_CANCELLED = object()

# How often the reader wakes to re-check the cancel flag, in seconds.
_CANCEL_POLL_INTERVAL = 0.05


class CancelledRender(Exception):
    """Raised when a pooled job is abandoned because the caller cancelled."""


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using %d", name, raw, default)
        return default
    if value < minimum:
        logger.warning("%s=%d below minimum %d; using %d", name, value, minimum, minimum)
        return minimum
    return value


def pool_size() -> int:
    """Configured worker count. 0 disables the pool entirely."""
    return _env_int("YANTRA4D_CQ_WORKERS", 2, minimum=0)


def max_jobs_per_worker() -> int:
    """Recycle a worker after this many jobs. 0 means never recycle."""
    return _env_int("YANTRA4D_CQ_WORKER_MAX_JOBS", 50, minimum=0)


def worker_startup_timeout() -> int:
    """Seconds to wait for a worker's readiness line (the cadquery import)."""
    return _env_int("YANTRA4D_CQ_WORKER_START_TIMEOUT_S", 120, minimum=1)


class _Worker:
    """One persistent cq_runner subprocess."""

    def __init__(self, env: dict | None = None):
        self.jobs_served = 0
        self.proc = subprocess.Popen(
            [sys.executable, RUNNER_SCRIPT, "--serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr stays separate so stray kernel chatter cannot corrupt the
            # JSON-lines stream we parse on stdout.
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
        )

    def await_ready(self, timeout: float) -> None:
        """Block until the worker reports a warm kernel. Raises on failure."""
        line = _readline_with_timeout(self.proc.stdout, timeout)
        if line is None:
            raise RuntimeError(
                f"CadQuery worker did not become ready within {timeout:g}s"
            )
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"CadQuery worker sent non-JSON readiness line: {exc}") from exc
        if not payload.get("ready"):
            raise RuntimeError(payload.get("error", "CadQuery worker failed to start"))

    def run(self, request: dict, timeout: float,
            is_cancelled: Callable[[], bool] | None = None) -> tuple[bool, str]:
        """Send one job and await its result.

        Raises TimeoutError on timeout, CancelledRender when *is_cancelled*
        turns true, and propagates protocol/IO errors.
        """
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        line = _readline_with_timeout(self.proc.stdout, timeout, is_cancelled)
        if line is _CANCELLED:
            raise CancelledRender("Render cancelled by user request")
        if line is None:
            raise TimeoutError(f"Render timed out after {int(timeout)} seconds")
        payload = json.loads(line)
        self.jobs_served += 1
        return bool(payload.get("ok")), payload.get("output", "")

    def alive(self) -> bool:
        return self.proc.poll() is None

    def kill(self) -> None:
        try:
            self.proc.kill()
            self.proc.wait(timeout=5)
        except Exception:
            logger.debug("Failed to kill CadQuery worker", exc_info=True)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass


def _readline_with_timeout(stream, timeout: float,
                           is_cancelled: Callable[[], bool] | None = None):
    """Read one line, giving up after *timeout* seconds or on cancellation.

    Returns the line, ``None`` on timeout, or ``_CANCELLED`` when *is_cancelled*
    turns true while waiting.

    ``stream.readline()`` on a pipe cannot be interrupted, so the read happens
    on a daemon thread and the caller abandons it. The abandoned thread dies
    with the process, which the pool kills on both of those paths anyway — a
    worker that timed out or was cancelled mid-job is never reused, because its
    kernel may still be churning on the abandoned solid.
    """
    result: list[str] = []

    def _read():
        try:
            line = stream.readline()
            if line:
                result.append(line)
        except Exception:
            pass

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()

    if is_cancelled is None:
        thread.join(timeout)
    else:
        # Wake periodically so a cancel is honoured promptly rather than only
        # after the full render timeout, matching the subprocess path's 50ms poll.
        deadline = time.monotonic() + timeout
        while thread.is_alive() and time.monotonic() < deadline:
            thread.join(_CANCEL_POLL_INTERVAL)
            if thread.is_alive() and is_cancelled():
                return _CANCELLED

    if thread.is_alive() or not result:
        return None
    return result[0].strip()


class CadQueryPool:
    """Lazily started pool of warm CadQuery workers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._idle: list[_Worker] = []
        self._live = 0
        self._disabled = False
        self._disabled_reason = ""

    # -- lifecycle ---------------------------------------------------------

    def _acquire(self, env: dict | None) -> _Worker | None:
        """Take an idle worker or start a new one. None if the pool is unusable."""
        size = pool_size()
        if size == 0:
            return None
        with self._lock:
            if self._disabled:
                return None
            while self._idle:
                worker = self._idle.pop()
                if worker.alive():
                    return worker
                # Died while idle; it no longer counts against capacity.
                self._live -= 1
                worker.kill()
            if self._live >= size:
                # Saturated. The caller spawns a one-shot rather than queueing,
                # which keeps latency bounded under burst.
                return None
            self._live += 1

        try:
            worker = _Worker(env=env)
            worker.await_ready(worker_startup_timeout())
            return worker
        except Exception as exc:
            with self._lock:
                self._live -= 1
                # A worker that cannot import cadquery will never succeed;
                # stop retrying on every render and let callers fall back.
                self._disabled = True
                self._disabled_reason = str(exc)
            logger.warning(
                "CadQuery warm pool unavailable (%s); falling back to per-render "
                "subprocess spawn", exc,
            )
            try:
                worker.kill()  # type: ignore[possibly-undefined]
            except Exception:
                pass
            return None

    def _release(self, worker: _Worker) -> None:
        """Return a healthy worker to the pool, recycling it if it is spent."""
        limit = max_jobs_per_worker()
        spent = limit and worker.jobs_served >= limit
        if spent or not worker.alive():
            if spent:
                logger.info(
                    "Recycling CadQuery worker after %d jobs", worker.jobs_served
                )
            self._discard(worker)
            return
        with self._lock:
            self._idle.append(worker)

    def _discard(self, worker: _Worker) -> None:
        """Kill a worker and free its slot."""
        worker.kill()
        with self._lock:
            self._live -= 1

    # -- public API --------------------------------------------------------

    def submit(
        self,
        script_path: str,
        output_path: str,
        params_json: str,
        export_format: str,
        env: dict | None = None,
        timeout: float | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[bool, str] | None:
        """Run one render on a warm worker.

        Returns ``(success, output)`` on completion, or **None** when the pool
        could not take the job — the caller must then fall back to a per-render
        subprocess spawn. None means "not handled", never "failed".
        """
        worker = self._acquire(env)
        if worker is None:
            return None

        deadline = timeout if timeout is not None else RENDER_TIMEOUT_S
        request = {
            "script_path": script_path,
            "output_path": output_path,
            "params_json": params_json,
            "export_format": export_format,
        }
        started = time.monotonic()
        try:
            success, output = worker.run(request, deadline, is_cancelled)
        except CancelledRender:
            # The worker is still evaluating the abandoned solid; killing it is
            # the only way to stop that work, and matches what cancelling the
            # one-shot subprocess did. Wording matches the subprocess path so
            # the render contract sees no difference.
            logger.info("CadQuery pooled render cancelled; killing worker")
            self._discard(worker)
            return False, "Render cancelled by user request"
        except TimeoutError as exc:
            # A wedged OCCT is unrecoverable in-process. Kill, do not reuse.
            logger.error("CadQuery worker timed out after %.1fs; killing worker",
                         time.monotonic() - started)
            self._discard(worker)
            return False, str(exc)
        except Exception as exc:
            logger.warning("CadQuery worker failed mid-job (%s); killing worker", exc)
            self._discard(worker)
            return None  # unproven job — let the caller retry via subprocess
        else:
            self._release(worker)
            return success, output

    def shutdown(self) -> None:
        """Kill every worker. For tests and clean process exit."""
        with self._lock:
            workers, self._idle = self._idle, []
            self._live -= len(workers)
            self._live = max(self._live, 0)
        for worker in workers:
            worker.kill()

    def reset(self) -> None:
        """Shut down and clear the disabled latch. For tests."""
        self.shutdown()
        with self._lock:
            self._disabled = False
            self._disabled_reason = ""
            self._live = 0

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": pool_size(),
                "live": self._live,
                "idle": len(self._idle),
                "disabled": self._disabled,
                "disabled_reason": self._disabled_reason,
            }


# Module-level singleton, mirroring render_cache's pattern.
cq_pool = CadQueryPool()
