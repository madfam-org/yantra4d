"""
Keep CadQuery execution in the render worker.

Every render runs on the render worker: the API queues the job and relays its
events (``render_orchestrator``, ``worker_dispatch``). An engine called from a
request handler would instead run inside a gunicorn worker, holding it for the
length of the render and bypassing the queue's cancellation, leases and
artifact handling. This decorator makes that a loud error rather than a quiet
regression: the CadQuery entry points refuse to run inside a Flask request
context, which the render worker never has.

The static half of the same guarantee is
``tests/unit/test_engine_guard.py``: no API module imports the CadQuery
engine, and the API app never loads it.
"""
from __future__ import annotations

import functools


class EngineInRequestError(RuntimeError):
    """A render engine was invoked from an API request handler."""


def _in_request_context() -> bool:
    try:
        from flask import has_request_context
    except ImportError:  # pragma: no cover - flask ships in every image
        return False
    return has_request_context()


def worker_only(fn):
    """Refuse to run *fn* inside a Flask request; see the module docstring."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if _in_request_context():
            raise EngineInRequestError(
                f"{fn.__module__}.{fn.__qualname__} runs on the render worker; "
                "queue the render (services.engine.worker_dispatch) instead of "
                "calling the engine from a request handler"
            )
        return fn(*args, **kwargs)

    return wrapper
