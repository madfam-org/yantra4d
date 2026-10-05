"""Tests for PUT /api/projects/<slug>/manifest/bindings — the graph editor's
fork-only write of manifest parameter `binding` entries."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

GRAPH = {
    "version": "1.0.0",
    "units": "mm",
    "nodes": [
        {"id": "outline", "type": "profile_circle", "params": {"r": 45}},
        {"id": "plate", "type": "extrude", "inputs": {"profile": "outline"}, "params": {"height": 8}},
        {"id": "edge", "type": "chamfer", "inputs": {"shape": "plate"}, "params": {"distance": 1}},
    ],
    "outputs": {"flange": "edge"},
}


def _manifest(slug, scad_file="part.graph.json"):
    return {
        "project": {"name": "Flange", "slug": slug, "version": "1.0.0"},
        "modes": [{
            "id": "main", "scad_file": scad_file, "label": {"en": "Main"},
            "parts": ["flange"], "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": "flange", "label": {"en": "Flange"}, "default_color": "#fff"}],
        "parameters": [
            {"id": "plate_radius", "type": "slider", "default": 45, "min": 15, "max": 120,
             "step": 1, "label": {"en": "Radius"}, "binding": "outline.r"},
            {"id": "plate_height", "type": "slider", "default": 8, "min": 2, "max": 30,
             "step": 1, "label": {"en": "Height"}},
            {"id": "edge_chamfer", "type": "slider", "default": 1, "min": 0.2, "max": 3,
             "step": 0.1, "label": {"en": "Chamfer"}},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }


def _make_project(root: Path, slug: str, source_type: str | None, scad_file="part.graph.json"):
    project_dir = root / slug
    project_dir.mkdir()
    (project_dir / "project.json").write_text(json.dumps(_manifest(slug, scad_file), indent=2) + "\n")
    if scad_file.endswith(".graph.json"):
        (project_dir / scad_file).write_text(json.dumps(GRAPH, indent=2) + "\n")
    else:
        (project_dir / scad_file).write_text("cube(10);")
    if source_type is not None:
        meta = {"source": {"type": source_type, "forked_from": "flange-plate"}}
        (project_dir / "project.meta.json").write_text(json.dumps(meta))
    return project_dir


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    _make_project(tmp_path, "my-flange", "fork")
    _make_project(tmp_path, "flange-plate", None)  # a commons cartridge: no meta
    _make_project(tmp_path, "imported-flange", "github")
    _make_project(tmp_path, "my-scad-fork", "fork", scad_file="main.scad")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _put(client, slug, body):
    data = body if isinstance(body, (str, bytes)) else json.dumps(body)
    return client.put(
        f"/api/projects/{slug}/manifest/bindings", data=data, content_type="application/json",
    )


def _params(tmp_path, slug):
    manifest = json.loads((tmp_path / slug / "project.json").read_text())
    return {p["id"]: p for p in manifest["parameters"]}


class TestSetAndClear:
    def test_sets_a_binding_on_an_existing_parameter(self, client, tmp_path):
        res = _put(client, "my-flange", {"bindings": {"plate_height": "plate.height"}})
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["bindings"] == {"plate_radius": "outline.r", "plate_height": "plate.height"}
        assert _params(tmp_path, "my-flange")["plate_height"]["binding"] == "plate.height"

    def test_accepts_a_list_of_targets(self, client, tmp_path):
        res = _put(client, "my-flange", {"bindings": {"plate_radius": ["outline.r", "plate.height"]}})
        assert res.status_code == 200, res.get_json()
        assert _params(tmp_path, "my-flange")["plate_radius"]["binding"] == ["outline.r", "plate.height"]

    def test_null_clears_a_binding(self, client, tmp_path):
        res = _put(client, "my-flange", {"bindings": {"plate_radius": None}})
        assert res.status_code == 200
        assert res.get_json()["bindings"] == {}
        assert "binding" not in _params(tmp_path, "my-flange")["plate_radius"]

    def test_set_and_clear_in_one_request_moves_a_binding(self, client, tmp_path):
        res = _put(client, "my-flange", {"bindings": {"plate_radius": None, "plate_height": "outline.r"}})
        assert res.status_code == 200, res.get_json()
        params = _params(tmp_path, "my-flange")
        assert "binding" not in params["plate_radius"]
        assert params["plate_height"]["binding"] == "outline.r"

    def test_leaves_every_other_manifest_field_untouched(self, client, tmp_path):
        before = json.loads((tmp_path / "my-flange" / "project.json").read_text())
        _put(client, "my-flange", {"bindings": {"edge_chamfer": "edge.distance"}})
        after = json.loads((tmp_path / "my-flange" / "project.json").read_text())
        after["parameters"][2].pop("binding")
        assert after == before
        assert list(after) == list(before)

    def test_write_leaves_no_temp_file_behind(self, client, tmp_path):
        _put(client, "my-flange", {"bindings": {"edge_chamfer": "edge.distance"}})
        leftovers = [p.name for p in (tmp_path / "my-flange").iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []


class TestRefusesNonForks:
    def test_refuses_a_commons_cartridge(self, client, tmp_path):
        before = (tmp_path / "flange-plate" / "project.json").read_text()
        res = _put(client, "flange-plate", {"bindings": {"plate_height": "plate.height"}})
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "not_a_fork"
        assert (tmp_path / "flange-plate" / "project.json").read_text() == before

    def test_refuses_an_imported_repository(self, client):
        res = _put(client, "imported-flange", {"bindings": {"plate_height": "plate.height"}})
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "not_a_fork"

    def test_refuses_an_unreadable_meta_file(self, client, tmp_path):
        (tmp_path / "my-flange" / "project.meta.json").write_text("{not json")
        res = _put(client, "my-flange", {"bindings": {"plate_height": "plate.height"}})
        assert res.status_code == 403

    def test_unknown_project_is_404(self, client):
        res = _put(client, "no-such-project", {"bindings": {"x": None}})
        assert res.status_code == 404


class TestStrictBody:
    @pytest.mark.parametrize("body", [
        "{nope",
        [],
        {},
        {"bindings": {}},
        {"bindings": []},
        {"bindings": {"plate_height": "plate.height"}, "parameters": []},
        {"bindings": {"plate_height": 3}},
        {"bindings": {"plate_height": "plate"}},
        {"bindings": {"plate_height": "plate.height; import os"}},
        {"bindings": {"plate_height": []}},
        {"bindings": {"plate_height": ["plate.height", "plate.height"]}},
        {"bindings": {"plate_height": ["outline.r"] * 51}},
    ])
    def test_rejects_malformed_bodies(self, client, tmp_path, body):
        before = (tmp_path / "my-flange" / "project.json").read_text()
        res = _put(client, "my-flange", body)
        assert res.status_code == 400, res.get_json()
        assert (tmp_path / "my-flange" / "project.json").read_text() == before

    def test_rejects_an_unknown_parameter(self, client):
        res = _put(client, "my-flange", {"bindings": {"brand_new": "plate.height"}})
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "unknown_parameter"

    def test_caps_the_body_size(self, client):
        huge = {"bindings": {"plate_height": "plate.height"}, "pad": "x" * (17 * 1024)}
        res = _put(client, "my-flange", huge)
        assert res.status_code == 413


class TestGraphAuthority:
    def test_rejects_a_binding_to_an_unknown_node(self, client, tmp_path):
        before = (tmp_path / "my-flange" / "project.json").read_text()
        res = _put(client, "my-flange", {"bindings": {"plate_height": "ghost.height"}})
        assert res.status_code == 400
        assert "ghost" in res.get_json()["error"]
        assert (tmp_path / "my-flange" / "project.json").read_text() == before

    def test_rejects_a_binding_to_an_unknown_param(self, client):
        res = _put(client, "my-flange", {"bindings": {"plate_height": "plate.depth"}})
        assert res.status_code == 400

    def test_rejects_binding_a_structural_param(self, client):
        res = _put(client, "my-flange", {"bindings": {"plate_height": "outline.plane"}})
        assert res.status_code == 400
        assert "cannot be bound" in res.get_json()["error"]

    def test_rejects_two_parameters_driving_one_target(self, client):
        res = _put(client, "my-flange", {"bindings": {"plate_height": "outline.r"}})
        assert res.status_code == 400
        assert "more than one parameter" in res.get_json()["error"]

    def test_rejects_a_project_without_a_graph_source(self, client):
        res = _put(client, "my-scad-fork", {"bindings": {"plate_height": "plate.height"}})
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "no_graph_source"
