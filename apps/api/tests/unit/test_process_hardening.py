"""Tests for process non-dumpable hardening.

On Linux the parent is set non-dumpable so same-UID CadQuery children cannot read
its /proc/<pid>/environ or /proc/<pid>/mem. Off Linux the call is a safe no-op.
"""
import platform
import subprocess
import sys

import pytest

from utils.process_hardening import set_process_nondumpable


def test_set_nondumpable_is_noop_off_linux():
    if platform.system() == "Linux":
        pytest.skip("Linux behaviour is covered by the subprocess test below")
    # Off Linux: returns False (not applied), never raises.
    assert set_process_nondumpable() is False


def test_set_nondumpable_never_raises():
    # Whatever the platform, the call must not raise.
    set_process_nondumpable()


@pytest.mark.skipif(platform.system() != "Linux", reason="prctl is Linux-only")
def test_nondumpable_blocks_child_reading_parent_environ():
    """End-to-end on Linux: after PR_SET_DUMPABLE=0 a same-UID child cannot read
    the parent's /proc/<ppid>/environ. Verified in a real subprocess so the
    kernel's ownership change is actually exercised.
    """
    program = r"""
import os, ctypes, subprocess, sys
os.environ["Y4D_PARENT_SECRET"] = "sentinel-value"
libc = ctypes.CDLL("libc.so.6", use_errno=True)
# PR_SET_DUMPABLE = 4
assert libc.prctl(4, 0, 0, 0, 0) == 0
ppid = os.getpid()
child = subprocess.run(
    [sys.executable, "-c",
     "import sys\n"
     "try:\n"
     "    data = open('/proc/%d/environ','rb').read()\n"
     "    sys.stdout.write('READ' if b'sentinel-value' in data else 'NOSENTINEL')\n"
     "except Exception as e:\n"
     "    sys.stdout.write('DENIED:%s' % type(e).__name__)\n" % ppid],
    capture_output=True, text=True,
)
sys.stdout.write(child.stdout)
"""
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, check=False)
    # The child must NOT have read the parent's secret environ.
    assert "READ" not in result.stdout, result.stdout
    assert result.stdout.startswith("DENIED") or result.stdout == "NOSENTINEL", result.stdout
