"""
Shared Render Engine Utilities
Provides common process management for OpenSCAD and CadQuery render engines.
Both engines share: RENDER_TIMEOUT_S, active-process tracking, and cancel logic.
"""
import logging
import subprocess
import threading

import os

logger = logging.getLogger(__name__)

RENDER_TIMEOUT_S = int(os.getenv("RENDER_TIMEOUT_S", 300))


class ProcessManager:
    """Thread-safe tracker for a single active render subprocess.

    Usage:
        pm = ProcessManager()
        process = pm.start(subprocess.Popen(...))
        # later…
        pm.cancel()
    """

    def __init__(self):
        self._active_process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def start(self, process: subprocess.Popen) -> subprocess.Popen:
        """Register *process* as the current active render and return it."""
        with self._lock:
            self._active_process = process
        return process

    def clear(self) -> None:
        """Deregister the active process (call after it finishes)."""
        with self._lock:
            self._active_process = None

    def cancel(self) -> bool:
        """Terminate the active process if one is running.

        Returns True if a process was cancelled, False if none was active.
        """
        with self._lock:
            proc = self._active_process
            if proc is None or proc.poll() is not None:
                return False
            logger.info("Cancelling active render process (pid=%s)", proc.pid)
            proc.terminate()

        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

        self.clear()
        return True
