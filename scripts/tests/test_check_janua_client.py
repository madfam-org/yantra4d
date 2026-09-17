"""scripts/qa/check_janua_client.py — the deploy reads its stdout.

`--print-client-id` feeds $GITHUB_OUTPUT, whose parser accepts only
`key=value` lines. The first production deploy after the manifest landed
(2026-09-17, run 35192561068) died at that step because the script also
printed its progress lines on stdout. These tests pin the contract: in print
mode stdout is exactly one `client_id=` line; in check mode the report is
human-facing and the exit code carries the verdict.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qa" / "check_janua_client.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_print_mode_stdout_is_exactly_the_output_line():
    result = _run("--print-client-id")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one line for $GITHUB_OUTPUT, got: {lines!r}"
    key, sep, value = lines[0].partition("=")
    assert (key, sep) == ("client_id", "=")
    assert value.startswith("jnc_") and " " not in value
    # The report still exists — on stderr, where the deploy log shows it.
    assert "checked:" in result.stderr


def test_check_mode_reports_on_stdout_and_passes():
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "OK: janua.client.yaml is consistent with deploy.yml" in result.stdout
    assert "client_id=" not in result.stdout
