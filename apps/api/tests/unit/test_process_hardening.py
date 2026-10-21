"""Tests for process non-dumpable hardening.

On Linux the parent is set non-dumpable so same-UID CadQuery children cannot read
its /proc/<pid>/environ or /proc/<pid>/mem. Off Linux the call is a safe no-op.
"""
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from utils.process_hardening import set_process_nondumpable

API_DIR = Path(__file__).resolve().parents[2]


def test_set_nondumpable_is_noop_off_linux():
    if platform.system() == "Linux":
        pytest.skip("Linux behaviour is covered by the subprocess test below")
    # Off Linux: returns False (not applied), never raises.
    assert set_process_nondumpable() is False


def test_set_nondumpable_never_raises():
    # Whatever the platform, the call must not raise.
    set_process_nondumpable()


def _has_cap_sys_ptrace() -> bool:
    """CAP_SYS_PTRACE (bit 19) in the effective set lets a reader bypass the
    non-dumpable check, so the test cannot demonstrate the property there."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("CapEff:"):
                return bool(int(line.split()[1], 16) & (1 << 19))
    except OSError:
        pass
    return False


# The parent process: probe its own environ through a same-UID child, set itself
# non-dumpable with the production helper, probe again. Prints "<before> <after>".
_PARENT = textwrap.dedent("""
    import os, subprocess, sys
    sys.path.insert(0, sys.argv[1])
    from utils.process_hardening import set_process_nondumpable

    CHILD = '''
    import sys
    try:
        with open("/proc/" + sys.argv[1] + "/environ", "rb") as handle:
            data = handle.read()
        sys.stdout.write("READ" if b"sentinel-value" in data else "NOSENTINEL")
    except PermissionError:
        sys.stdout.write("DENIED")
    '''

    def probe():
        out = subprocess.run(
            [sys.executable, "-c", CHILD, str(os.getpid())],
            capture_output=True, text=True, check=False,
        )
        return out.stdout.strip() or "ERR:" + out.stderr.strip()[-200:]

    before = probe()
    applied = set_process_nondumpable()
    after = probe()
    sys.stdout.write(before + " " + str(applied) + " " + after)
""")


@pytest.mark.skipif(platform.system() != "Linux", reason="prctl is Linux-only")
def test_nondumpable_blocks_child_reading_parent_environ():
    """End-to-end on Linux, in a real process tree.

    The sentinel is set in the parent's environment at exec time, so it is in
    /proc/<pid>/environ. Before hardening a same-UID child reads it; after
    ``set_process_nondumpable()`` the same child gets PermissionError.
    """
    if _has_cap_sys_ptrace():
        pytest.skip("CAP_SYS_PTRACE bypasses the non-dumpable check; cannot demonstrate here")
    env = dict(os.environ, Y4D_PARENT_SECRET="sentinel-value")
    result = subprocess.run(
        [sys.executable, "-c", _PARENT, str(API_DIR)],
        capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 0, result.stderr
    before, applied, after = result.stdout.split()
    if before != "READ":
        pytest.skip(f"this environment does not let a same-UID child read /proc environ ({before})")
    assert applied == "True"
    assert after == "DENIED", result.stdout
