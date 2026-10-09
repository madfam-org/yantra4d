"""A healthy previous deployment must never accept a new renderer release."""
import importlib.util
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_probe", ROOT / "scripts/ci/wait_for_render_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.fixture
def clock(monkeypatch):
    now = [0]
    monkeypatch.setattr(release.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(release.time, "sleep", lambda delay: now.__setitem__(0, now[0] + delay))


@pytest.mark.parametrize("response", [
    (200, {"status": "healthy", "render_revision": "old"}),
    (200, {"status": "healthy"}),
    (503, {"status": "unhealthy", "render_revision": "new"}),
    (200, {}),
    (200, []),
])
def test_old_or_unready_backend_cannot_accept_new_release(monkeypatch, clock, response):
    monkeypatch.setattr(release, "probe", lambda *_: response)
    assert release.wait_for_release("https://example.test/ready", "new", timeout=2, interval=1) == 1


def test_rollout_transport_failure_then_old_then_new(monkeypatch, clock):
    probe = Mock(side_effect=[ValueError("502 HTML"),
                             (200, {"status": "healthy", "render_revision": "old"}),
                             (200, {"status": "healthy", "render_revision": "new"})])
    monkeypatch.setattr(release, "probe", probe)
    assert release.wait_for_release("https://example.test/ready", "new", timeout=3, interval=1) == 0
    assert probe.call_count == 3


def test_frontend_only_publish_checks_availability(monkeypatch, clock):
    monkeypatch.setattr(release, "probe", lambda *_: (200, {"status": "healthy", "render_revision": "old"}))
    assert release.wait_for_release("https://example.test/ready", "") == 0


def test_workflow_uses_same_identity_for_build_and_verification():
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
    jobs = workflow["jobs"]
    verify = jobs["verify-deploy"]
    assert "build-backend" in verify["needs"]
    build = next(s for s in jobs["build-backend"]["steps"] if s.get("name") == "Build and push")
    step = next(s for s in verify["steps"] if s.get("name") == "Wait for the serving renderer release")
    # A failed-jobs rerun may reuse a successful backend from attempt1 while
    # verification runs at attempt2. Read that build's saved output, never
    # reconstruct identity from the verifier's current github.run_attempt.
    assert step["env"]["RENDER_BUILD_ID"] == "${{ needs.build-backend.outputs.render_revision }}"
    identity = next(s for s in jobs["build-backend"]["steps"] if s.get("id") == "render-identity")
    assert jobs["build-backend"]["outputs"]["render_revision"] == "${{ steps.render-identity.outputs.value }}"
    assert "RENDER_BUILD_ID=${{ steps.render-identity.outputs.value }}" in build["with"]["build-args"]
    assert "github.run_attempt" in identity["env"]["BUILD_ID"]
    assert 'test -n "$RENDER_BUILD_ID"' in step["run"]
    assert '--expected-revision "$EXPECTED"' in step["run"]
    assert '"$BACKEND_RESULT" = success' in step["run"]


@pytest.mark.parametrize("result,identity,expected_status", [
    ("success", "source-run-1", 0),
    ("success", "", 1),
    ("skipped", "", 0),
])
def test_verifier_shell_reuses_producing_identity(tmp_path, result, identity, expected_status):
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
    step = next(s for s in workflow["jobs"]["verify-deploy"]["steps"] if s.get("run"))
    binary = tmp_path / "python3"
    binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$RECORDED_ARGS"\n')
    binary.chmod(0o755)
    recorded = tmp_path / "args"
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               BACKEND_RESULT=result, RENDER_BUILD_ID=identity, GITHUB_RUN_ATTEMPT="2",
               RECORDED_ARGS=str(recorded))
    command = subprocess.run(["bash", "-e", "-c", step["run"]], env=env,
                             capture_output=True, text=True, check=False)
    assert command.returncode == expected_status, command.stderr
    if expected_status:
        assert not recorded.exists(), "missing identity must not degrade to an availability-only check"
    else:
        assert recorded.read_text().splitlines() == [
            "scripts/ci/wait_for_render_release.py", "--expected-revision", identity,
        ]
