"""An in-memory Redis that runs the real render worker inline, for route tests.

Routes that render queue a task on ``RENDER_QUEUE`` and wait on the job's
pub/sub channels. ``InlineRenderRedis`` stands in for Redis on both sides: when
a task is pushed it is handed straight to ``render_worker.process_sync_task`` /
``process_stream_task`` (the real functions), whose published events land in
the subscriber the route opened before pushing. Only the engines are faked, so
a test exercises route -> queue -> worker -> channels -> route end to end.

Not a test module (no ``test_`` prefix); imported by the e2e/unit tests.
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parents[2] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))


class _PubSub:
    def __init__(self, owner: InlineRenderRedis):
        self._owner = owner
        self.channels: set[str] = set()
        self.messages: deque = deque()
        self.closed = False

    def subscribe(self, *channels):
        self.channels.update(channels)

    def get_message(self, timeout=None):
        if self.messages:
            return self.messages.popleft()
        return None

    def close(self):
        self.closed = True
        if self in self._owner.subscribers:
            self._owner.subscribers.remove(self)


class InlineRenderRedis:
    """The Redis surface the render orchestrator and worker use, in memory."""

    def __init__(self, queue_name: str, *, run_inline: bool = True):
        self.queue_name = queue_name
        self.run_inline = run_inline
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set] = {}
        self.lists: dict[str, list] = {}
        self.subscribers: list[_PubSub] = []
        self.pushed: list[dict] = []
        self.published: list[tuple[str, dict]] = []
        self.worker = None  # set by the fixture

    # -- strings ---------------------------------------------------------
    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None):
        self.kv[key] = str(value)
        return True

    def delete(self, *keys):
        removed = 0
        for key in keys:
            removed += int(self.kv.pop(key, None) is not None)
        return removed

    def expire(self, key, seconds):
        return key in self.kv

    # -- sets ------------------------------------------------------------
    def sadd(self, key, *members):
        self.sets.setdefault(key, set()).update(members)

    def srem(self, key, *members):
        self.sets.setdefault(key, set()).difference_update(members)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def scard(self, key):
        return len(self.sets.get(key, set()))

    # -- lists -----------------------------------------------------------
    def rpush(self, key, value):
        if key == self.queue_name:
            task = json.loads(value)
            self.pushed.append(task)
            if self.run_inline and self.worker is not None:
                if task.get("stream"):
                    self.worker.process_stream_task(task)
                else:
                    self.worker.process_sync_task(task)
                return 1
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    def llen(self, key):
        return len(self.lists.get(key, []))

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])
        return list(items[start:] if end == -1 else items[start:end + 1])

    def lrem(self, key, count, value):
        items = self.lists.get(key, [])
        before = len(items)
        self.lists[key] = [item for item in items if item != value]
        return before - len(self.lists[key])

    # -- pub/sub ---------------------------------------------------------
    def pubsub(self, ignore_subscribe_messages=True):
        sub = _PubSub(self)
        self.subscribers.append(sub)
        return sub

    def publish(self, channel, message):
        try:
            self.published.append((channel, json.loads(message)))
        except (TypeError, ValueError):
            self.published.append((channel, {"raw": message}))
        delivered = 0
        for sub in list(self.subscribers):
            if channel in sub.channels:
                sub.messages.append({"type": "message", "channel": channel, "data": message})
                delivered += 1
        return delivered

    # -- helpers ---------------------------------------------------------
    def beat(self, heartbeat_key: str):
        """Publish a fresh worker heartbeat so the API sees a live worker."""
        self.kv[heartbeat_key] = str(int(time.time()))


def install(monkeypatch, static_dir: Path, *, run_inline: bool = True):
    """Point the orchestrator and the worker at one inline Redis; return it.

    Also points every module-level STATIC_FOLDER the render path reads at
    *static_dir*, so nothing is written into the repository's static folder.
    """
    import render_worker

    from config import Config
    from services.engine import render_orchestrator

    static_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
    monkeypatch.setattr(render_orchestrator, "STATIC_FOLDER", str(static_dir))
    monkeypatch.setattr(render_worker, "STATIC_FOLDER", str(static_dir))
    for module_name in ("routes.projects.animations", "routes.editor.git_ops"):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, "STATIC_FOLDER"):
            monkeypatch.setattr(module, "STATIC_FOLDER", str(static_dir))

    fake = InlineRenderRedis(render_orchestrator.RENDER_QUEUE, run_inline=run_inline)
    fake.worker = render_worker
    monkeypatch.setattr(render_orchestrator, "r", fake)
    monkeypatch.setattr(render_worker, "r", fake)
    fake.beat(render_orchestrator.RENDER_WORKER_HEARTBEAT_KEY)
    return fake
