"""Process-level hardening for the CadQuery-executing parents.

A CadQuery cartridge runs as a subprocess of the render worker (and, for a couple
of routes, of the API's gunicorn workers). That subprocess runs under the same UID
as its parent, so by default it could read the parent's ``/proc/<ppid>/environ``
and ``/proc/<ppid>/mem`` — which is where the parent's object-store credentials and
app secrets live. The subprocess env is already minimised, but the parent's is not
and cannot be.

Setting the parent process non-dumpable (``PR_SET_DUMPABLE = 0``) makes the kernel
own ``/proc/<pid>`` with restrictive permissions, so a same-UID child can no longer
read the parent's environ or memory. This is the single cheap control that closes
the "child reads parent's secrets" path regardless of what the child imports.

Linux-only (the mechanism is ``prctl``). On any other platform this is a no-op and
says so, rather than pretending to harden. Production runs on Linux, which is where
it matters; local macOS development simply skips it.
"""

from __future__ import annotations

import ctypes
import logging
import platform

logger = logging.getLogger(__name__)

# <linux/prctl.h>
_PR_SET_DUMPABLE = 4
_PR_GET_DUMPABLE = 3


def set_process_nondumpable() -> bool:
    """Make this process non-dumpable so same-UID children cannot read its memory.

    Returns True when the process is confirmed non-dumpable afterwards, False
    otherwise (non-Linux, or the prctl call did not take). Never raises: a
    hardening step must not crash the process it is protecting.
    """
    if platform.system() != "Linux":
        logger.info(
            "Process non-dumpable hardening skipped: not Linux (%s)",
            platform.system(),
        )
        return False
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        rc = libc.prctl(_PR_SET_DUMPABLE, 0, 0, 0, 0)
        if rc != 0:
            logger.warning(
                "prctl(PR_SET_DUMPABLE, 0) returned %d (errno %d); process stays dumpable",
                rc, ctypes.get_errno(),
            )
            return False
        # Confirm the flag actually took, rather than trusting the return code.
        dumpable = libc.prctl(_PR_GET_DUMPABLE, 0, 0, 0, 0)
        if dumpable == 0:
            logger.info("Process set non-dumpable (PR_SET_DUMPABLE=0)")
            return True
        logger.warning("Process still reports dumpable=%d after PR_SET_DUMPABLE", dumpable)
        return False
    except Exception:
        logger.warning("Could not set process non-dumpable", exc_info=True)
        return False
