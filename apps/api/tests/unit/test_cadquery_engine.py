import pytest
import os
import json
from unittest.mock import patch, MagicMock
from services.engine.cadquery_engine import _cadquery_env, build_cadquery_command, run_render, stream_render, cancel_render

def test_cadquery_env(monkeypatch):
    monkeypatch.setattr("config.Config.PROJECTS_DIR", "/fake/proj")
    # if it had pre-existing pythonpath, we ensure it prepend
    monkeypatch.setenv("PYTHONPATH", "/old/path")
    env = _cadquery_env()
    assert "/fake/proj" in env["PYTHONPATH"]
    assert "/old/path" in env["PYTHONPATH"]

    monkeypatch.delenv("PYTHONPATH", raising=False)
    env2 = _cadquery_env()
    assert env2["PYTHONPATH"] == "/fake/proj"

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
