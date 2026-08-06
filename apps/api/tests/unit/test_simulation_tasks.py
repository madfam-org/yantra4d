"""
Unit tests for tasks/simulation_tasks.py
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_queue_simulation_returns_job_id():
    from tasks.simulation_tasks import queue_simulation
    job_id = queue_simulation("test-slug", [{"id": "housing"}], {"housing": {"pinned": True}})
    assert isinstance(job_id, str)
    assert len(job_id) == 36  # UUID format


def test_get_job_status_queued_initially():
    from tasks.simulation_tasks import get_job_status, queue_simulation
    job_id = queue_simulation("demo", [{"id": "body"}], {})
    status = get_job_status(job_id)
    assert status is not None
    assert status["status"] in ("queued", "running")
    assert status["slug"] == "demo"


def test_get_job_status_unknown_returns_none():
    from tasks.simulation_tasks import get_job_status
    result = get_job_status("00000000-0000-0000-0000-000000000000")
    assert result is None


def test_simulation_completes_with_frames():
    """Simulation should complete and set status=success with frames populated."""
    from tasks.simulation_tasks import get_job_status, queue_simulation
    job_id = queue_simulation("sentinel-gripper", [{"id": "housing"}], {"housing": {"pinned": True}})

    # Poll for up to 15 seconds (mock runs ~3s)
    deadline = time.time() + 15
    while time.time() < deadline:
        status = get_job_status(job_id)
        if status["status"] == "success":
            break
        time.sleep(0.3)

    assert status["status"] == "success"
    assert isinstance(status["frames"], list)
    assert len(status["frames"]) == 100


def test_simulation_progress_increases():
    """Progress should reach 100 on success."""
    from tasks.simulation_tasks import get_job_status, queue_simulation
    job_id = queue_simulation("test", [{"id": "body"}], {})

    deadline = time.time() + 15
    while time.time() < deadline:
        status = get_job_status(job_id)
        if status["status"] == "success":
            break
        time.sleep(0.3)

    assert status["progress"] == pytest.approx(100.0)


def test_separate_jobs_have_independent_state():
    """Two concurrent jobs must not share state."""
    from tasks.simulation_tasks import get_job_status, queue_simulation
    job1 = queue_simulation("proj-a", [{"id": "a"}], {})
    job2 = queue_simulation("proj-b", [{"id": "b"}], {})
    assert job1 != job2
    s1 = get_job_status(job1)
    s2 = get_job_status(job2)
    assert s1["slug"] == "proj-a"
    assert s2["slug"] == "proj-b"
