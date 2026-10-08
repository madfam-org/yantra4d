"""
Contract tests for routes/engine/simulate.py

Each endpoint says what it actually computed: physics fails closed without a
solver backend, and the stress map and the parameter search are estimates.
"""
import json
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

SLUG = "sim-test"


@pytest.fixture
def client(tmp_path):
    project_dir = tmp_path / SLUG
    project_dir.mkdir()
    manifest = {
        "project": {"name": "Simulation Test", "slug": SLUG, "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["body"]}],
        "parts": [{"id": "body", "label": {"en": "Body"}, "default_color": "#3498db"}],
        "parameters": [],
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    yield app.test_client()

    from tasks.simulation_tasks import configure_physics_solver
    configure_physics_solver(None)


PHYSICS_BODY = {"parts": [{"id": "body"}], "kinematics": {"body": {"pinned": True}}}


def test_physics_answers_501_without_a_solver(client):
    res = client.post(f"/api/projects/{SLUG}/simulate/physics", json=PHYSICS_BODY)
    assert res.status_code == 501
    body = res.get_json()
    assert body["status"] == "error"
    assert body["error_code"] == "physics_solver_unavailable"
    assert "job_id" not in body


def test_physics_fails_closed_before_reading_the_payload(client):
    res = client.post(f"/api/projects/{SLUG}/simulate/physics", json={})
    assert res.status_code == 501
    assert res.get_json()["error_code"] == "physics_solver_unavailable"


def test_physics_with_a_solver_reports_the_solver_frames(client):
    from tasks.simulation_tasks import configure_physics_solver
    configure_physics_solver(lambda script, part_count: ["frame-000.ply"])

    res = client.post(f"/api/projects/{SLUG}/simulate/physics", json=PHYSICS_BODY)
    assert res.status_code == 202
    job_id = res.get_json()["job_id"]

    deadline = time.time() + 5
    status = client.get(f"/api/projects/{SLUG}/simulate/physics/{job_id}").get_json()
    while status["status"] != "success" and time.time() < deadline:
        time.sleep(0.01)
        status = client.get(f"/api/projects/{SLUG}/simulate/physics/{job_id}").get_json()
    assert status["status"] == "success"
    assert status["frames"] == ["frame-000.ply"]
    assert status["frames_generated"] == 1


def test_physics_with_a_solver_still_requires_parts_and_kinematics(client):
    from tasks.simulation_tasks import configure_physics_solver
    configure_physics_solver(lambda script, part_count: [])
    res = client.post(f"/api/projects/{SLUG}/simulate/physics", json={"parts": []})
    assert res.status_code == 400


def test_physics_status_of_an_unknown_job_is_404(client):
    res = client.get(f"/api/projects/{SLUG}/simulate/physics/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_optimize_is_labelled_a_heuristic_estimate(client):
    res = client.post(f"/api/projects/{SLUG}/simulate/optimize", json={"params": {"wall_thickness": 2.0}})
    assert res.status_code == 202
    started = res.get_json()
    assert started["method"] == "heuristic"
    assert started["approximation"] is True

    url = f"/api/projects/{SLUG}/simulate/optimize/{started['job_id']}"
    deadline = time.time() + 10
    status = client.get(url).get_json()
    while status["status"] not in ("success", "failed") and time.time() < deadline:
        time.sleep(0.05)
        status = client.get(url).get_json()
    assert status["status"] == "success"
    assert status["method"] == "heuristic"
    assert status["approximation"] is True
    assert "current_sigma" not in status
    assert isinstance(status["current_score"], float)
    assert status["logs"] and all("heuristic score" in line for line in status["logs"])
    assert not any("sigma" in line for line in status["logs"])


def test_stress_is_labelled_a_geometry_estimate(client, monkeypatch):
    from routes.engine import simulate

    @contextmanager
    def fake_local_artifact(key):
        yield Path("/nonexistent/mesh.stl")

    summary = {"schema_version": "stress_proxy_v1", "approximation": True}
    monkeypatch.setattr(simulate, "find_latest_render_key", lambda slug: f"renders/{slug}/mesh.stl")
    monkeypatch.setattr(simulate, "local_artifact", fake_local_artifact)
    monkeypatch.setattr(simulate, "compute_stress_field", lambda path, force_vector: {"summary": summary})

    res = client.post(f"/api/projects/{SLUG}/simulate/stress", json={"force_y": -50.0})
    assert res.status_code == 200
    body = res.get_json()
    assert body["method"] == "geometry_proxy"
    assert body["approximation"] is True
    assert body["simulation"]["summary"]["schema_version"] == "stress_proxy_v1"
