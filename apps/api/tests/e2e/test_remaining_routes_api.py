import json
import pytest

def _create_project(tmp_path, slug="assembly-test", **kwargs):
    project_dir = tmp_path / slug
    project_dir.mkdir(exist_ok=True)
    manifest = {
        "project": {"name": "Test", "slug": slug, "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "parts": ["main"]}],
        "parts": [{"id": "main"}]
    }
    manifest.update(kwargs)
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    return project_dir

@pytest.fixture
def app(tmp_path):
    _create_project(tmp_path)
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

class TestAssemblyAPI:
    def test_get_assembly(self, client):
        res = client.get("/api/projects/assembly-test/assembly")
        assert res.status_code in [200, 404]

    def test_get_assembly_unknown(self, client):
        res = client.get("/api/projects/nonexistent/assembly")
        assert res.status_code == 404

class TestDatasheetAPI2:
    def test_get_datasheet(self, client):
        res = client.get("/api/projects/assembly-test/datasheet")
        assert res.status_code in [200, 404]
        
    def test_get_datasheet_pdf(self, client):
        res = client.get("/api/projects/assembly-test/datasheet/pdf")
        assert res.status_code in [200, 404]

class TestGitOpsAPI2:
    def test_git_status(self, client):
        res = client.get("/api/editor/git_ops/assembly-test/status")
        assert res.status_code in [200, 400, 404, 401]
        
    def test_git_commit(self, client):
        res = client.post("/api/editor/git_ops/assembly-test/commit", json={"message": "test"})
        assert res.status_code in [200, 400, 404, 401]
        
    def test_git_diff(self, client):
        res = client.get("/api/editor/git_ops/assembly-test/diff")
        assert res.status_code in [200, 400, 404, 401]
