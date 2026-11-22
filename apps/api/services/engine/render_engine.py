"""
Shared Render Engine Utilities
Provides common process management for OpenSCAD and CadQuery render engines.
Both engines share: RENDER_TIMEOUT_S, active-process tracking, and cancel logic.
"""
import logging
import os
import signal
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RENDER_TIMEOUT_S = int(os.getenv("RENDER_TIMEOUT_S", "300"))


@dataclass
class RenderResult:
    """Structured result from a render subprocess.

    Supports tuple unpacking for backward compatibility:
        success, stderr = run_render(cmd)
    """
    success: bool
    stderr: str
    output_path: str | None = None
    duration_ms: float | None = None

    def __iter__(self):
        """Allow ``success, stderr = result`` unpacking."""
        yield self.success
        yield self.stderr


#: Signals that mean the engine process itself crashed in native code (OCCT,
#: VTK, OpenBLAS, the interpreter). Deliberately not here: SIGKILL (our own
#: timeout and cancel, and the kernel's OOM killer), SIGXCPU (the CPU-time
#: limit, which a visitor's parameters can reach) and SIGTERM (a shutdown).
CRASH_SIGNALS = frozenset(
    int(getattr(signal, name))
    for name in ("SIGSEGV", "SIGBUS", "SIGILL", "SIGFPE", "SIGABRT")
    if hasattr(signal, name)
)


def crash_signal_of(returncode: int | None) -> int | None:
    """The crash signal a render process died of, or ``None``.

    ``subprocess`` reports death by signal N as return code ``-N``. Read from
    the process's exit status, never from its output: the output echoes the
    visitor's parameters.
    """
    if not isinstance(returncode, int) or isinstance(returncode, bool) or returncode >= 0:
        return None
    return -returncode if -returncode in CRASH_SIGNALS else None


class EngineResult(tuple):
    """``(success, output)`` from an engine run, plus how the process died.

    A plain two-tuple to every caller that unpacks or compares it. The
    ``crash_signal`` attribute carries ``crash_signal_of`` for the render
    worker, which reports it on the part's error event.
    """

    crash_signal: int | None

    def __new__(cls, success: bool, output: str, crash_signal: int | None = None):
        self = super().__new__(cls, (success, output))
        self.crash_signal = crash_signal
        return self


class ProcessManager:
    """Track render processes without letting one request cancel another.

    Request-scoped callers pass their own process to cancel/clear. Legacy
    callers without a process retain the most-recent-active behavior.
    """

    def __init__(self):
        self._active_process: subprocess.Popen | None = None
        self._processes: list[subprocess.Popen] = []
        self._lock = threading.Lock()

    def start(self, process: subprocess.Popen) -> subprocess.Popen:
        """Register *process* as active and return it."""
        with self._lock:
            if not any(item is process for item in self._processes):
                self._processes.append(process)
            self._active_process = process
        return process

    def _forget_locked(self, process: subprocess.Popen) -> None:
        self._processes = [item for item in self._processes if item is not process]
        self._active_process = self._processes[-1] if self._processes else None

    def clear(self, process: subprocess.Popen | None = None) -> None:
        """Deregister only the finishing request, preserving overlapping work."""
        with self._lock:
            target = process if process is not None else self._active_process
            if target is not None:
                self._forget_locked(target)

    def cancel(self, process: subprocess.Popen | None = None) -> bool:
        """Terminate the named process (or the latest for legacy callers)."""
        with self._lock:
            proc = process if process is not None else self._active_process
            if proc is None or not any(item is proc for item in self._processes):
                return False
            if proc.poll() is not None:
                self._forget_locked(proc)
                return False
            logger.info("Cancelling render process (pid=%s)", proc.pid)
            try:
                proc.terminate()
            except ProcessLookupError:
                self._forget_locked(proc)
                return False

        try:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        finally:
            self.clear(proc)
        return True


def communicate_cancellable(
    process: subprocess.Popen,
    is_cancelled: Callable[[], bool],
    cancel: Callable[[], bool],
) -> tuple[str, str | None]:
    """Drain both pipes while retaining cancellation and the caller's deadline.

    Waiting for exit before communicate() deadlocks when a renderer fills its
    stdout/stderr pipe. Repeated timed communicate() calls keep draining and
    retain collected output across TimeoutExpired, while polling cancellation.
    The caller continues to own its kill timer and process-manager cleanup.
    """
    while True:
        if is_cancelled():
            cancel()
        try:
            return process.communicate(timeout=0.05)
        except subprocess.TimeoutExpired:
            continue
