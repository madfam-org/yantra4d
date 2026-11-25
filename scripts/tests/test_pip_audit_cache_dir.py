"""Every pip-audit call in a workflow must pass an explicit `--cache-dir`.

Run standalone (there is no root pytest config):

    python3 -m pytest scripts/tests/test_pip_audit_cache_dir.py -q

Without one, pip-audit asks platformdirs for its default cache
(`~/.cache/pip-audit`). platformdirs 4.14.8 (2026-11-20) refuses to create a
private user directory below a world-writable, non-sticky ancestor, and the
ARC runners' `/home/runner` is mode 0777. The `backend` job in ci.yml runs on
madfam-runners-blue on a push to main, so its `pip-audit --desc` died there
with `PermissionError: /home/runner, writable by another user` before
auditing anything (pull requests run on hosted ubuntu-24.04 and never saw it).
pip-audit passes an explicit `--cache-dir` through without calling
platformdirs, so the job points it at a directory it creates under
$RUNNER_TEMP.

Stdlib-and-regex only, like test_ruff_pin.py: the lane that runs scripts/tests
installs pytest and jsonschema, not PyYAML, and a guard that skipped for want
of a parser would be no guard at all. So instead of walking parsed `run:`
values it reads the workflow text line by line, drops YAML keys other than
`run:` and comments, and joins `\\` continuations.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW_FILES = sorted(
    [*(REPO / ".github" / "workflows").glob("*.yml"),
     *(REPO / ".github" / "workflows").glob("*.yaml"),
     *(REPO / ".github" / "actions").glob("**/*.yml"),
     *(REPO / ".github" / "actions").glob("**/*.yaml")]
)
CI = REPO / ".github" / "workflows" / "ci.yml"

# A command that runs pip-audit, as a module or as the console script; not an
# install of it.
PIP_AUDIT_CALL = re.compile(r"(\bpip_audit\b|(^|[\s/;&|(])pip-audit(\s|$))")
# A YAML mapping key at the start of a line (`name:`, `- uses:`, `with:` ...).
YAML_KEY = re.compile(r"^(-\s+)?[A-Za-z_][\w-]*:(\s|$)")
RUN_KEY = re.compile(r"^(-\s+)?run:\s*")


def _commands(text: str) -> list[str]:
    """Shell-looking lines of a workflow file, with `\\` continuations joined.

    A `run:` key is kept with its inline value (`- run: pip-audit`); every
    other key line (`- name: Audit with pip-audit`) and every comment is
    dropped, so a step name or a comment that mentions pip-audit is not read
    as a call.
    """
    commands, current = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not current:
            if not line or line.startswith("#"):
                continue
            if RUN_KEY.match(line):
                line = RUN_KEY.sub("", line, count=1)
                if line in ("", "|", ">", "|-", ">-"):
                    continue
            elif YAML_KEY.match(line):
                continue
        if line.endswith("\\"):
            current += line[:-1].rstrip() + " "
            continue
        commands.append(current + line)
        current = ""
    if current:
        commands.append(current)
    return commands


def _audit_without_cache_dir(text: str) -> list[str]:
    return [
        command
        for command in _commands(text)
        if PIP_AUDIT_CALL.search(command)
        and "install" not in command.split()
        and not command.startswith("echo ")
        and "--cache-dir" not in command
    ]


def test_every_pip_audit_call_passes_a_cache_dir():
    assert WORKFLOW_FILES, "no workflow files found"
    offenders = [
        f"{path.relative_to(REPO)}: {command}"
        for path in WORKFLOW_FILES
        for command in _audit_without_cache_dir(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_backend_job_still_audits():
    """The fix must not be to drop the audit: the gate stays in place."""
    calls = [c for c in _commands(CI.read_text(encoding="utf-8"))
             if PIP_AUDIT_CALL.search(c) and "install" not in c.split()]
    assert any(c.startswith("pip-audit --desc") for c in calls), calls


def test_the_cache_dir_is_created_before_use():
    """pip-audit does not create a missing --cache-dir parent with mode 700."""
    text = CI.read_text(encoding="utf-8")
    create = text.find('install -d -m 700 "$RUNNER_TEMP/pip-audit-cache"')
    use = text.find('--cache-dir "$RUNNER_TEMP/pip-audit-cache"')
    assert create != -1 and use != -1 and create < use


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("      - run: pip-audit --desc", ["pip-audit --desc"]),
        ('      - run: pip-audit --desc --cache-dir "$RUNNER_TEMP/c"', []),
        (
            "        run: |\n          python -m pip_audit -r r.txt",
            ["python -m pip_audit -r r.txt"],
        ),
        ("        run: |\n          pip-audit -r r.txt \\\n            --strict",
         ["pip-audit -r r.txt --strict"]),
        ('        run: |\n          pip-audit -r r.txt \\\n            --cache-dir "$RUNNER_TEMP/c"',
         []),
        ('      - run: pip install "ruff==0.16.5" "pip-audit==2.10.1"', []),
        ("      - name: Audit with pip-audit", []),
        ("      # pip-audit needs a cache dir", []),
        ('          echo "run pip-audit locally"', []),
    ],
)
def test_pip_audit_call_detection(text, expected):
    assert _audit_without_cache_dir(text) == expected
