import json
import os
from unittest.mock import MagicMock, patch

from services.engine.cadquery_engine import (
    _cadquery_env,
    build_cadquery_command,
    cancel_render,
    run_render,
    stream_render,
)


def test_cadquery_env(monkeypatch):
    # Both cartridge roots land on PYTHONPATH (RFC 0038 P2): a CadQuery script
    # in a client-private cartridge imports its siblings like a public one. The
    # child's PYTHONPATH is ONLY the curated roots — the parent's PYTHONPATH (the
    # app package) is deliberately not inherited.
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/private")
    monkeypatch.setenv("PYTHONPATH", "/old/path")
    env = _cadquery_env()
    assert "/fake/proj" in env["PYTHONPATH"]
    assert "/fake/private" in env["PYTHONPATH"]
    # The parent's pre-existing PYTHONPATH is not carried into the child.
    assert "/old/path" not in env["PYTHONPATH"]
    # The public commons is searched first.
    parts = env["PYTHONPATH"].split(os.pathsep)
    assert parts.index("/fake/proj") < parts.index("/fake/private")

    monkeypatch.delenv("PYTHONPATH", raising=False)
    env2 = _cadquery_env()
    assert env2["PYTHONPATH"] == os.pathsep.join(["/fake/proj", "/fake/private"])


def test_cadquery_env_single_root_when_private_is_unset(monkeypatch):
    # A deployment with one cartridge root gets exactly one entry, not a
    # duplicate of the same directory.
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/proj")
    monkeypatch.delenv("PYTHONPATH", raising=False)
    assert _cadquery_env()["PYTHONPATH"] == "/fake/proj"

def test_cadquery_env_never_includes_the_user_projects_root(monkeypatch):
    # User-named directories must not be importable by name from the runner:
    # a fork or import called `cadquery` would otherwise be imported by
    # cq_runner itself, outside the sandbox. Only curated roots are on the path.
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/private")
    monkeypatch.setattr("config.Config.USER_PROJECTS_DIR", "/fake/user")
    monkeypatch.delenv("PYTHONPATH", raising=False)
    parts = _cadquery_env()["PYTHONPATH"].split(os.pathsep)
    assert parts == ["/fake/proj", "/fake/private"]
    assert "/fake/user" not in parts


def test_build_cadquery_command():
    cmd = build_cadquery_command("out.stl", "script.py", {"p": 1}, "STL")
    assert cmd[0] == "python"
    assert "cq_runner.py" in cmd[1]
    assert cmd[2] == "script.py"
    assert cmd[3] == "out.stl"
    assert '{"p": 1}' in cmd[4]
    assert cmd[5] == "STL"

@patch("services.engine.cadquery_engine.subprocess.run")
def test_run_render_success(mock_run):
    mock_run.return_value = MagicMock(stdout="done", stderr=" ok")
    success, out = run_render(["cmd"])
    assert success is True
    assert out == "done ok"

@patch("services.engine.cadquery_engine.subprocess.run")
def test_run_render_timeout(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired(["cmd"], 300)
    success, out = run_render(["cmd"])
    assert success is False
    assert "timed out" in out

@patch("services.engine.cadquery_engine.subprocess.run")
def test_run_render_error(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"], output="out", stderr="err")
    success, out = run_render(["cmd"])
    assert success is False
    assert out == "outerr"

@patch("services.engine.cadquery_engine.subprocess.Popen")
@patch("services.engine.cadquery_engine.threading.Timer")
def test_stream_render_success(mock_timer_cls, mock_popen):
    mock_proc = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = ['Building shape\n', '']
    mock_proc.stdout = mock_stdout
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc
    
    events = list(stream_render(["cmd"], "part1", 0, 100, 1, 1))
    
    # Assert there's part_start, output, part_done
    event_types = [json.loads(e)["event"] for e in events]
    assert "part_start" in event_types
    assert "output" in event_types
    assert "part_done" in event_types

@patch("services.engine.cadquery_engine.subprocess.Popen")
@patch("services.engine.cadquery_engine.threading.Timer")
def test_stream_render_failure(mock_timer_cls, mock_popen):
    mock_proc = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = ['']
    mock_proc.stdout = mock_stdout
    mock_proc.returncode = 1
    mock_popen.return_value = mock_proc
    
    events = list(stream_render(["cmd"], "part1", 0, 100, 1, 1))
    event_types = [json.loads(e)["event"] for e in events]
    assert "error" in event_types

@patch("services.engine.cadquery_engine._cq_process_manager")
def test_cancel_render(mock_mgr):
    mock_mgr.cancel.return_value = True
    assert cancel_render() is True


# ── minimal child environment (no app/object-store secrets reach the child) ─────
def test_cadquery_env_excludes_object_store_and_app_secrets(monkeypatch):
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/private")
    for leaky in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AI_API_KEY",
                  "COTIZA_WEBHOOK_SECRET", "TIER_OVERRIDES", "JANUA_ISSUER",
                  "RENDER_ARTIFACT_S3_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(leaky, "should-not-leak")
    env = _cadquery_env()
    for leaky in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AI_API_KEY",
                  "COTIZA_WEBHOOK_SECRET", "TIER_OVERRIDES", "JANUA_ISSUER",
                  "RENDER_ARTIFACT_S3_SECRET_ACCESS_KEY"):
        assert leaky not in env, f"{leaky} leaked into the CadQuery child env"


def test_cadquery_env_keeps_needed_vars(monkeypatch):
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/private")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("CASROOT", "/opt/occt")
    monkeypatch.setenv("FONTCONFIG_FILE", "/etc/fonts/fonts.conf")
    env = _cadquery_env()
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["CASROOT"] == "/opt/occt"
    assert env["FONTCONFIG_FILE"] == "/etc/fonts/fonts.conf"
    # HOME is set to a writable location for libraries that cache under it.
    assert env.get("HOME")
    # The curated roots are handed to the runner for its import allowlist.
    assert "/fake/proj" in env["YANTRA4D_CURATED_ROOTS"]


def test_cadquery_env_pythonpath_is_only_curated_roots(monkeypatch):
    # The parent's PYTHONPATH (the app package) must not be inherited by the child.
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", "/fake/private")
    monkeypatch.setenv("PYTHONPATH", "/app/backend")
    env = _cadquery_env()
    parts = env["PYTHONPATH"].split(os.pathsep)
    assert "/app/backend" not in parts
    assert parts == ["/fake/proj", "/fake/private"]
