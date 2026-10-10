"""Manual verification defaults to no issue writes; scheduled reporting stays on."""
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/spec-nightly.yml").read_text())
STEPS = WORKFLOW["jobs"]["full-render-sweep"]["steps"]


def test_manual_issue_writes_require_opt_in():
    # PyYAML's YAML 1.1 loader calls the Actions `on` key True.
    dispatch = WORKFLOW.get("on", WORKFLOW.get(True))["workflow_dispatch"]
    assert dispatch["inputs"]["report_to_issue"]["default"] is False
    reporters = [s for s in STEPS if "tracking issue" in s.get("name", "")]
    assert len(reporters) == 2
    for step in reporters:
        assert "(github.event_name != 'workflow_dispatch' || inputs.report_to_issue)" in step["if"]


@pytest.mark.parametrize("enabled,expected_calls", [("false", 1), ("true", 2)])
def test_fixture_command_only_reports_when_enabled(tmp_path, enabled, expected_calls):
    step = next(s for s in STEPS if s.get("name") == "Reporter dry run (fixture, no rendering)")
    binary = tmp_path / "python3"
    binary.write_text(
        "#!/usr/bin/env python3\n"  # replaced below with the current interpreter
        "import json,sys\n"
        "with open('calls.jsonl','a') as out: out.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    import sys
    binary.write_text(binary.read_text().replace("#!/usr/bin/env python3", "#!" + sys.executable))
    binary.chmod(0o755)
    fixture = tmp_path / 'fixture$(touch should-not-exist).txt'
    fixture.write_text("fixture")
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               REPORT_FIXTURE=str(fixture), REPORT_TO_ISSUE=enabled)
    result = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(calls) == expected_calls
    assert calls[0] == [".github/scripts/nightly_report.py", "--selftest", str(fixture)]
    if enabled == "true":
        assert "--log" in calls[1]
    assert not (tmp_path / "should-not-exist").exists()
