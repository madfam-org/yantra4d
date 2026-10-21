"""
Unit tests for tasks/simulation_tasks.py

No physics solver ships with the API, so a job may only exist once a solver
backend is registered, and its frames must be exactly what that solver returned.
"""
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture(autouse=True)
def _no_solver_after_test():
    yield
    from tasks.simulation_tasks import configure_physics_solver
    configure_physics_solver(None)


def _wait_for_terminal(job_id, timeout=5.0):
    from tasks.simulation_tasks import get_job_status
    deadline = time.time() + timeout
    status = get_job_status(job_id)
    while time.time() < deadline and status["status"] not in ("success", "failed"):
        time.sleep(0.01)
        status = get_job_status(job_id)
    return status


def test_without_a_solver_no_job_is_created():
    from tasks.simulation_tasks import (
        _JOB_STORE,
        PhysicsSolverUnavailable,
        physics_solver_available,
        queue_simulation,
    )
    before = len(_JOB_STORE)
    assert physics_solver_available() is False
    with pytest.raises(PhysicsSolverUnavailable):
        queue_simulation("demo", [{"id": "body"}], {"body": {"pinned": True}})
    assert len(_JOB_STORE) == before


def test_configuring_a_solver_makes_physics_available():
    from tasks.simulation_tasks import configure_physics_solver, physics_solver_available
    configure_physics_solver(lambda script, part_count: [])
    assert physics_solver_available() is True
    configure_physics_solver(None)
    assert physics_solver_available() is False


def test_job_reports_the_frames_the_solver_returned():
    from tasks.simulation_tasks import configure_physics_solver, queue_simulation
    calls = []

    def solver(script, part_count):
        calls.append((script, part_count))
        return ["frame-000.ply", "frame-001.ply"]

    configure_physics_solver(solver)
    job_id = queue_simulation("sentinel-gripper", [{"id": "housing"}], {"housing": {"pinned": True}})
    assert len(job_id) == 36  # UUID format

    status = _wait_for_terminal(job_id)
    assert status["status"] == "success"
    assert status["frames"] == ["frame-000.ply", "frame-001.ply"]
    assert status["frames_generated"] == 2
    assert status["progress"] == pytest.approx(100.0)
    assert status["error"] is None
    assert status["duration_ms"] is not None
    assert len(status["metadata"]["script_signature"]) == 12
    # The solver received the generated PPF script, not a placeholder.
    assert len(calls) == 1
    script, part_count = calls[0]
    assert isinstance(script, str) and script
    assert part_count == 1


def test_solver_failure_marks_the_job_failed_without_frames():
    from tasks.simulation_tasks import configure_physics_solver, queue_simulation

    def solver(script, part_count):
        raise RuntimeError("solver diverged")

    configure_physics_solver(solver)
    status = _wait_for_terminal(queue_simulation("demo", [{"id": "body"}], {"body": {}}))
    assert status["status"] == "failed"
    assert status["error"] == "solver diverged"
    assert status["frames"] == []
    assert status["frames_generated"] == 0


def test_job_is_running_while_the_solver_works():
    from tasks.simulation_tasks import configure_physics_solver, get_job_status, queue_simulation
    release = threading.Event()

    def solver(script, part_count):
        release.wait(5)
        return []

    configure_physics_solver(solver)
    job_id = queue_simulation("demo", [{"id": "body"}], {"body": {}})
    deadline = time.time() + 5
    while time.time() < deadline and get_job_status(job_id)["status"] != "running":
        time.sleep(0.01)
    status = get_job_status(job_id)
    assert status["status"] == "running"
    assert status["frames"] == []
    release.set()
    assert _wait_for_terminal(job_id)["status"] == "success"


def test_get_job_status_unknown_returns_none():
    from tasks.simulation_tasks import get_job_status
    assert get_job_status("00000000-0000-0000-0000-000000000000") is None


def test_separate_jobs_have_independent_state():
    from tasks.simulation_tasks import configure_physics_solver, get_job_status, queue_simulation
    configure_physics_solver(lambda script, part_count: [])
    job1 = queue_simulation("proj-a", [{"id": "a"}], {"a": {}})
    job2 = queue_simulation("proj-b", [{"id": "b"}], {"b": {}})
    assert job1 != job2
    assert get_job_status(job1)["slug"] == "proj-a"
    assert get_job_status(job2)["slug"] == "proj-b"
