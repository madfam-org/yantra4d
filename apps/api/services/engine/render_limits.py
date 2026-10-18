"""Per-process resource limits for render subprocesses (OpenSCAD, CadQuery).

The render worker shares one container memory limit (2Gi in
``k8s/production/yantra4d-backend-deployment.yaml``) between itself, the warm
CadQuery workers and every render in flight. Without a per-process ceiling a
single runaway render grows until the kernel OOM-kills the container, and
every other render with it. With one, the runaway render fails on its own
(``MemoryError`` / ``std::bad_alloc``, or SIGXCPU for CPU time) and the worker
reports a render error.

Limits are applied in the child between ``fork`` and ``exec`` through
``preexec_fn``. The function only calls ``resource.setrlimit`` with values
computed in the parent, so it takes no locks and imports nothing in the child.

Tunables (read when a render starts, so a changed env takes effect without a
restart of the module):

* ``RENDER_RLIMIT_AS_MB`` — address-space ceiling per render process.
  Default 1536: below the 2Gi container limit with room for the worker itself.
  ``0`` disables it.
* ``RENDER_RLIMIT_CPU_S`` — CPU-seconds ceiling per one-shot render process.
  Default ``RENDER_TIMEOUT_S + 60``: the wall-clock timeout normally ends a
  render first; this is the backstop if that timer does not fire. ``0``
  disables it.

Platforms without the ``resource`` module (Windows) run renders unlimited, as
before. The address-space limit (and the ``MALLOC_ARENA_MAX`` cap that goes
with it) is applied on Linux only — see ``address_space_limit_enforced``.
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable

from services.engine.render_engine import RENDER_TIMEOUT_S

try:  # POSIX only
    import resource
except ImportError:  # pragma: no cover - exercised only on platforms without it
    resource = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_AS_MB = 1536
DEFAULT_CPU_S = RENDER_TIMEOUT_S + 60

#: glibc reserves 64 MiB of address space per malloc arena and creates up to
#: 8 arenas per core for multithreaded programs (OCCT meshing, manifold/TBB).
#: That reservation is address space, not memory, but RLIMIT_AS counts it, so
#: on a many-core node a render could be refused while using a fraction of its
#: ceiling. Capping the arena count keeps the address-space limit a memory limit.
MALLOC_ARENA_MAX = "2"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using %d", name, raw, default)
        return default
    if value < 0:
        logger.warning("%s=%d is negative; using %d", name, value, default)
        return default
    return value


def address_space_limit_bytes() -> int:
    """The configured RLIMIT_AS in bytes; 0 means unlimited."""
    return _env_int("RENDER_RLIMIT_AS_MB", DEFAULT_AS_MB) * 1024 * 1024


def cpu_limit_seconds() -> int:
    """The configured per-render RLIMIT_CPU in seconds; 0 means unlimited."""
    return _env_int("RENDER_RLIMIT_CPU_S", DEFAULT_CPU_S)


def limits_supported() -> bool:
    return resource is not None


def address_space_limit_enforced() -> bool:
    """RLIMIT_AS is applied on Linux only.

    macOS refuses an RLIMIT_AS below the address space a process already maps
    (its shared region alone is hundreds of GiB), so setting it there would
    fail every spawn; it does not enforce the limit anyway.
    """
    return resource is not None and sys.platform.startswith("linux")


def _within_hard(kind: int, soft: int, hard: int) -> tuple[int, int]:
    """Clamp to the hard limit this process already has: an unprivileged
    process may lower its limits but never raise the maximum, and a container
    runtime may have set one below ours."""
    current_hard = resource.getrlimit(kind)[1]
    if current_hard != resource.RLIM_INFINITY:
        hard = min(hard, current_hard)
        soft = min(soft, hard)
    return soft, hard


def render_preexec_fn(cpu_seconds: int | None = None) -> Callable[[], None] | None:
    """A ``preexec_fn`` applying the render limits, or ``None`` when none apply.

    *cpu_seconds* overrides the CPU ceiling (the warm pool passes a lifetime
    budget, since RLIMIT_CPU counts every job a persistent worker serves).
    """
    if resource is None:
        return None
    as_bytes = address_space_limit_bytes() if address_space_limit_enforced() else 0
    cpu_s = cpu_limit_seconds() if cpu_seconds is None else cpu_seconds
    limits: list[tuple[int, tuple[int, int]]] = []
    if as_bytes > 0:
        limits.append((resource.RLIMIT_AS, _within_hard(resource.RLIMIT_AS, as_bytes, as_bytes)))
    if cpu_s > 0:
        # Soft limit sends SIGXCPU (default action: terminate); the hard limit
        # one second later sends SIGKILL if the process ignores it.
        limits.append((resource.RLIMIT_CPU, _within_hard(resource.RLIMIT_CPU, cpu_s, cpu_s + 1)))
    if not limits:
        return None
    setrlimit = resource.setrlimit

    def _apply() -> None:
        for kind, value in limits:
            setrlimit(kind, value)

    return _apply


def limited_env(env: dict | None) -> dict | None:
    """*env* with ``MALLOC_ARENA_MAX`` set when the address-space limit is active.

    ``None`` (inherit the parent's environment) stays ``None`` unless the limit
    is active, in which case a copy of ``os.environ`` is returned with the cap.
    An explicit ``MALLOC_ARENA_MAX`` already present is kept.
    """
    if not address_space_limit_enforced() or address_space_limit_bytes() <= 0:
        return env
    child = dict(os.environ if env is None else env)
    child.setdefault("MALLOC_ARENA_MAX", MALLOC_ARENA_MAX)
    return child


def describe_exit(returncode: int | None) -> str | None:
    """A human reason for a render process killed by one of these limits."""
    if returncode is None or resource is None:
        return None
    import signal
    if returncode == -signal.SIGXCPU:
        return ("Render stopped: it exceeded its CPU-time limit "
                f"(RENDER_RLIMIT_CPU_S={cpu_limit_seconds()})")
    return None
