"""Public build identity for render cache isolation across image releases."""
import os
import uuid

# Without a build identity, never reuse another process's artifacts through Redis.
# Browser persistence is disabled in that case; no identity is advertised to it.
_PROCESS_REVISION = uuid.uuid4().hex


def render_revision() -> str:
    return os.environ.get("RENDER_BUILD_ID", "").strip()


def cache_revision() -> str:
    return render_revision() or _PROCESS_REVISION
