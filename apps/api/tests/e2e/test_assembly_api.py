import json
from unittest.mock import patch

import pytest


@pytest.fixture
def app(tmp_path):
    project_dir = tmp_path / "assemble-test"
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project": {"name": "Assemble Test", "slug": "assemble-test", "version": "1.0"},
        "assembly_steps": [{"step": 1, "label": "manual1", "notes": "", "_auto_generated": False}]
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube();")
    
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    
    # Needs PROJECTS_DIR setup like conftest
    flask_app.config["PROJECTS_DIR"] = tmp_path
    return flask_app

@pytest.fixture
def client(app, monkeypatch, tmp_path):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    return app.test_client()

class TestAssemblyAPI:
    @patch("routes.projects.assembly.analyze_directory")
    @patch("routes.projects.assembly.generate_assembly_steps")
    def test_get_assembly_steps(self, mock_gen, mock_analyze, client):
        mock_analyze.return_value = {"nodes": []}
        mock_gen.return_value = [{"step": 2, "label": "auto2", "_auto_generated": True}]
        
        res = client.get("/api/projects/assemble-test/assembly-steps")
        assert res.status_code == 200
        data = res.get_json()
        assert data["slug"] == "assemble-test"
        assert data["has_manual_steps"] is True
        assert data["step_count"] == 1
        assert "assembly_steps" in data

    def test_get_assembly_steps_not_found(self, client):
        res = client.get("/api/projects/unknown/assembly-steps")
        assert res.status_code == 404

    @patch("routes.projects.assembly.analyze_directory")
    def test_get_assembly_steps_analyze_fails(self, mock_analyze, client):
        mock_analyze.side_effect = Exception("failed analysis")
        res = client.get("/api/projects/assemble-test/assembly-steps")
        assert res.status_code == 500

    @patch("routes.projects.assembly.analyze_directory")
    @patch("routes.projects.assembly.generate_assembly_steps")
    def test_get_assembly_steps_generation_fails(self, mock_gen, mock_analyze, client):
        mock_analyze.return_value = {}
        mock_gen.side_effect = Exception("generation error")
        res = client.get("/api/projects/assemble-test/assembly-steps")
        assert res.status_code == 500

    @patch("routes.projects.assembly.analyze_directory")
    @patch("routes.projects.assembly.generate_assembly_steps")
    @patch("routes.projects.assembly.merge_assembly_steps")
    def test_write_assembly_steps(self, mock_merge, mock_gen, mock_analyze, client, tmp_path):
        mock_analyze.return_value = {}
        mock_gen.return_value = [{"step": 2, "label": "auto2", "_auto_generated": True}]
        mock_merge.return_value = [{"step": 1, "label": "manual1", "notes": "", "_auto_generated": False}, {"step": 2, "label": "auto2", "_auto_generated": True}]
        
        # 1. Merge = True
        res = client.post("/api/projects/assemble-test/assembly-steps/write", json={"merge": True})
        assert res.status_code == 200
        data = res.get_json()
        assert data["merged"] is True

        # Check project.json updated
        manifest = json.loads((tmp_path / "assemble-test" / "project.json").read_text())
        assert len(manifest["assembly_steps"]) == 2  # manual1 + auto2
        assert manifest["assembly_steps"][1]["label"] == "auto2"

    @patch("routes.projects.assembly.analyze_directory")
    @patch("routes.projects.assembly.generate_assembly_steps")
    def test_write_assembly_steps_no_merge(self, mock_gen, mock_analyze, client, tmp_path):
        mock_analyze.return_value = {}
        mock_gen.return_value = [{"step": 1, "label": "auto1", "_auto_generated": True}]
        
        # 2. Merge = False
        res = client.post("/api/projects/assemble-test/assembly-steps/write", json={"merge": False})
        assert res.status_code == 200
        data = res.get_json()
        assert data["merged"] is False
        
        manifest = json.loads((tmp_path / "assemble-test" / "project.json").read_text())
        # The single manual step is overwritten
        assert len(manifest["assembly_steps"]) == 1
        assert manifest["assembly_steps"][0]["label"] == "auto1"

    def test_write_assembly_steps_not_found(self, client):
        res = client.post("/api/projects/unknown/assembly-steps/write", json={})
        assert res.status_code == 404

    @patch("routes.projects.assembly.analyze_directory")
    def test_write_assembly_steps_fails(self, mock_analyze, client):
        mock_analyze.side_effect = Exception("failure")
        res = client.post("/api/projects/assemble-test/assembly-steps/write", json={"merge": True})
        assert res.status_code == 500
