import json

import pytest


def _create_project(tmp_path, slug="store-test"):
    project_dir = tmp_path / slug
    project_dir.mkdir(exist_ok=True)
    manifest = {
        "project": {"name": "Store Test", "slug": slug, "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "estimate": 100}],
        "estimate_constants": {"base": 1},
        "verification": [],
        "parameter_groups": [],
        "export_formats": [],
        "parameters": [
            {"id": "hidden_param", "hidden": True},
            {"id": "mode_param", "visible_in_modes": ["other"]},
            {"id": "dev_param", "group": "dev", "visibility_level": 1, "visible_in_modes": ["default"]},
            {"id": "normal_param"}
        ],
        "presets": [
            {"id": "p1", "label": "Preset 1", "values": {"normal_param": 10}}
        ]
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
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

class TestStorefrontAPI:
    def test_get_storefront_manifest(self, client):
        res = client.get("/api/projects/store-test/storefront")
        assert res.status_code == 200
        data = res.get_json()
        assert data["slug"] == "store-test"
        assert data["storefront"] is True
        
        manifest = data["manifest"]
        assert "estimate_constants" not in manifest
        assert "verification" not in manifest
        
        # Check params stripped
        params = manifest["parameters"]
        # hidden_param removed, normal_param and dev_param (without dev fields) should remain
        assert len(params) == 3
        
        # Check mode stripped
        mode = manifest["modes"][0]
        assert "scad_file" not in mode
        assert "estimate" not in mode
        
    def test_get_storefront_manifest_not_found(self, client):
        res = client.get("/api/projects/missing/storefront")
        assert res.status_code == 404

    def test_get_storefront_manifest_mode_filter(self, client):
        res = client.get("/api/projects/store-test/storefront?mode=default")
        assert res.status_code == 200
        data = res.get_json()
        params = data["manifest"]["parameters"]
        # hidden removed, mode_param removed (since mode="default" but it's only in "other"), 
        # dev_param stays, normal_param stays
        param_ids = [p["id"] for p in params]
        assert "dev_param" in param_ids
        assert "normal_param" in param_ids
        assert "mode_param" not in param_ids

    def test_get_share_url(self, client):
        res = client.get("/api/projects/store-test/share/p1")
        assert res.status_code == 200
        data = res.get_json()
        assert data["preset_id"] == "p1"
        assert data["preset_label"] == "Preset 1"
        assert data["values"] == {"normal_param": 10}
        assert "share_url" in data
        assert "preset=p1" in data["share_url"]
        assert "normal_param=10" in data["share_url"]
        # Regression: URL must use path-based format, never hash fragment
        assert "/project/store-test?" in data["share_url"]
        assert "#" not in data["share_url"]

    def test_get_share_url_not_found_project(self, client):
        res = client.get("/api/projects/missing/share/p1")
        assert res.status_code == 404

    def test_get_share_url_not_found_preset(self, client):
        res = client.get("/api/projects/store-test/share/missing")
        assert res.status_code == 404
