"""
Unit tests for tasks/optimization_tasks.py and services/simulation/optimizer.py
"""
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ─── TopologyOptimizer ────────────────────────────────────────────────────────

class TestTopologyOptimizer:
    def _make_optimizer(self, params=None):
        from services.simulation.optimizer import TopologyOptimizer
        return TopologyOptimizer("test-slug", params or {"blade_thickness": 2.0})

    def test_instantiation(self):
        opt = self._make_optimizer()
        assert opt.slug == "test-slug"
        assert opt.best_sigma == float("inf")

    def test_step_returns_dict(self):
        opt = self._make_optimizer()
        result = opt.step(1)
        assert isinstance(result, dict)
        assert "iteration" in result
        assert "current_sigma" in result
        assert "best_sigma" in result
        assert "testing_params" in result

    def test_step_iteration_matches(self):
        opt = self._make_optimizer()
        result = opt.step(7)
        assert result["iteration"] == 7

    def test_best_sigma_tracks_minimum(self):
        """After N steps, best_sigma should be <= first sigma encountered."""
        opt = self._make_optimizer()
        first = opt.step(1)
        first_sigma = first["current_sigma"]
        for i in range(2, 10):
            opt.step(i)
        assert opt.best_sigma <= first_sigma

    def test_best_params_updated_on_improvement(self):
        """best_params should reflect the parameters that produced min sigma."""
        opt = self._make_optimizer({"blade_thickness": 2.0})
        for i in range(1, 16):
            opt.step(i)
        assert "blade_thickness" in opt.best_params
        assert isinstance(opt.best_params["blade_thickness"], float)


# ─── Optimization Task Queue ──────────────────────────────────────────────────

class TestOptimizationTasks:
    def test_queue_returns_job_id(self):
        from tasks.optimization_tasks import queue_optimization
        job_id = queue_optimization("demo", {"blade_thickness": 2.0})
        assert isinstance(job_id, str)
        assert len(job_id) == 36

    def test_initial_status_queued_or_running(self):
        from tasks.optimization_tasks import queue_optimization, get_opt_status
        job_id = queue_optimization("demo", {"blade_thickness": 2.0})
        status = get_opt_status(job_id)
        assert status["status"] in ("queued", "running")
        assert status["slug"] == "demo"

    def test_unknown_job_returns_none(self):
        from tasks.optimization_tasks import get_opt_status
        assert get_opt_status("00000000-0000-0000-0000-000000000000") is None

    def test_optimization_completes(self):
        """Full optimization loop should complete and produce best_params."""
        from tasks.optimization_tasks import queue_optimization, get_opt_status
        job_id = queue_optimization("sentinel-gripper", {"blade_thickness": 2.0})

        # 15 gens × 0.4s/step = ~6s; allow 20s
        deadline = time.time() + 20
        while time.time() < deadline:
            status = get_opt_status(job_id)
            if status["status"] == "success":
                break
            time.sleep(0.5)

        assert status["status"] == "success"
        assert status["best_params"] is not None
        assert "blade_thickness" in status["best_params"]

    def test_optimization_logs_populated(self):
        """Completed jobs should expose human-readable generation logs."""
        from tasks.optimization_tasks import queue_optimization, get_opt_status
        job_id = queue_optimization("demo", {"blade_thickness": 2.0})

        deadline = time.time() + 20
        while time.time() < deadline:
            status = get_opt_status(job_id)
            if status["status"] == "success":
                break
            time.sleep(0.5)

        logs = status.get("logs", [])
        assert len(logs) > 0
        # Each log should mention generation and sigma
        assert any("Sigma" in line or "Gen" in line for line in logs)

    def test_two_jobs_independent(self):
        from tasks.optimization_tasks import queue_optimization, get_opt_status
        j1 = queue_optimization("proj-a", {"blade_thickness": 1.0})
        j2 = queue_optimization("proj-b", {"blade_thickness": 3.0})
        assert j1 != j2
        assert get_opt_status(j1)["slug"] == "proj-a"
        assert get_opt_status(j2)["slug"] == "proj-b"
