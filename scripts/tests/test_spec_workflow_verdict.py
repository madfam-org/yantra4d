"""Execute the workflow's real shell bodies against a failing checker.

An implicit Actions shell uses bash -e, which made tee conceal spec failures.
These tests use each step's declared shell and exercise its actual pipeline.
"""
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ("spec-nightly.yml", "full-render-sweep", "Full render sweep"),
    ("ci.yml", "spec-conformance", "Structural conformance (full commons)"),
    ("ci.yml", "spec-conformance", "Render conformance (changed cartridges)"),
]


def run_step(tmp_path, case, exit_code, populated=True):
    workflow, job, name = case
    doc = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())
    step = next(s for s in doc["jobs"][job]["steps"] if s.get("name") == name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    checker = bin_dir / "y4d-spec"
    checker.write_text(
        "#!/usr/bin/env python3\nimport json,sys\n"
        "json.dump(sys.argv[1:], open('arguments.json','w'))\n"
        "print('FAIL example: broken geometry', file=sys.stderr)\n"
        f"sys.exit({exit_code})\n"
    )
    checker.chmod(0o755)
    git = bin_dir / "git"
    git.write_text("#!/bin/sh\n[ \"$1\" != diff ] || echo projects/example/main.py\nexit 0\n")
    git.chmod(0o755)
    (tmp_path / "projects/libs").mkdir(parents=True)
    (tmp_path / "projects/commons-lib").mkdir()
    if populated:
        (tmp_path / "projects/example").mkdir()
        (tmp_path / "projects/example/project.json").write_text("{}")
    script = step["run"].replace("${{ github.event_name }}", "push").replace(
        "${{ github.event.before }}", "before"
    ).replace("${{ github.event.pull_request.base.sha }}", "base")
    command = ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail"] if step.get("shell") == "bash" else ["bash", "-e"]
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
               GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    return subprocess.run(command + ["-c", script], cwd=tmp_path, env=env,
                          capture_output=True, text=True)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("exit_code", [0, 7])
def test_checker_exit_survives_tee(tmp_path, case, exit_code):
    result = run_step(tmp_path, case, exit_code)
    assert result.returncode == exit_code, result.stderr
    args = json.loads((tmp_path / "arguments.json").read_text())
    assert "projects/example" in args
    assert "projects/libs" not in args and "projects/commons-lib" not in args
    assert "FAIL example" in result.stdout  # stderr is retained in the report
    if "Structural" not in case[2]:
        assert "--require-openscad" in args
        paths = [args[i + 1] for i, value in enumerate(args) if value == "--openscad-path"]
        assert paths == [str(tmp_path / "libs"), str(tmp_path / "projects/commons-lib")]


@pytest.mark.parametrize("case", CASES[:2])
def test_empty_full_sweep_fails_closed(tmp_path, case):
    result = run_step(tmp_path, case, 0, populated=False)
    assert result.returncode != 0
    assert not (tmp_path / "arguments.json").exists()
