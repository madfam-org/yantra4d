"""Tests for manifest.py — ProjectManifest, load/get/discover/invalidate_cache."""
import json

import pytest

from manifest import (
    ProjectManifest,
    discover_projects,
    get_manifest,
    invalidate_cache,
    load_manifest,
    _manifest_cache,
)


def _write_manifest(tmp_path, slug="demo", extra=None):
    """Helper: write a minimal valid project.json and return its dir."""
    project_dir = tmp_path / slug
    project_dir.mkdir(exist_ok=True)
    data = {
        "project": {"name": "Demo", "slug": slug, "version": "1.0.0", "description": "A demo project"},
        "modes": [{"id": "single", "scad_file": "main.scad", "label": "Single", "parts": ["body"], "estimate": {"base_units": 1}}],
        "parts": [{"id": "body", "render_mode": 0, "label": "Body", "default_color": "#cccccc"}],
        "parameters": [{"id": "width", "type": "slider", "default": 10, "min": 1, "max": 100, "label": "Width"}],
        "estimate_constants": {"base_time": 2, "per_unit": 1, "per_part": 0.5},
    }
    if extra:
        data.update(extra)
    (project_dir / "project.json").write_text(json.dumps(data))
    (project_dir / "main.scad").write_text("cube([10,10,10]);")
    return project_dir


# ---- ProjectManifest accessors ----

class TestProjectManifest:
    def test_slug(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.slug == "demo"

    def test_modes(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert len(m.modes) == 1
        assert m.modes[0]["id"] == "single"

    def test_get_allowed_files(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        allowed = m.get_allowed_files()
        assert "main.scad" in allowed
        assert allowed["main.scad"] == d / "main.scad"

    def test_get_parts_for_mode(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.get_parts_for_mode("single") == ["body"]
        assert m.get_parts_for_mode("nonexistent") == []

    def test_get_scad_file_for_mode(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.get_scad_file_for_mode("single") == "main.scad"
        assert m.get_scad_file_for_mode("nonexistent") is None

    def test_calculate_estimate_units(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.calculate_estimate_units("single", {}) == 1

    def test_as_json(self, tmp_path):
        d = _write_manifest(tmp_path)
        raw = json.loads((d / "project.json").read_text())
        m = ProjectManifest(raw, d)
        assert m.as_json() == raw


# ---- discover_projects ----

class TestDiscoverProjects:
    def test_discovers_project(self, tmp_path):
        _write_manifest(tmp_path, "alpha")
        _write_manifest(tmp_path, "beta")
        projects = discover_projects()
        slugs = [p["slug"] for p in projects]
        assert "alpha" in slugs
        assert "beta" in slugs

    def test_no_path_key(self, tmp_path):
        _write_manifest(tmp_path, "alpha")
        projects = discover_projects()
        for p in projects:
            assert "path" not in p

    def test_empty_projects_dir(self, tmp_path):
        # tmp_path exists but has no subdirs with project.json
        projects = discover_projects()
        assert projects == []

    def test_invalid_json_skipped(self, tmp_path):
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "project.json").write_text("{invalid json")
        projects = discover_projects()
        assert len(projects) == 0


# ---- load_manifest / get_manifest ----

class TestLoadManifest:
    def test_loads_and_caches(self, tmp_path):
        _write_manifest(tmp_path, "test")
        m1 = load_manifest("test")
        m2 = get_manifest("test")
        assert m1 is m2

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="not found"):
            load_manifest("nonexistent")

    def test_invalid_json_raises(self, tmp_path):
        bad_dir = tmp_path / "badjson"
        bad_dir.mkdir()
        (bad_dir / "project.json").write_text("{bad")
        with pytest.raises(RuntimeError, match="invalid JSON"):
            load_manifest("badjson")


# ---- invalidate_cache ----

class TestInvalidateCache:
    def test_invalidate_forces_reload(self, tmp_path):
        _write_manifest(tmp_path, "cached")
        m1 = load_manifest("cached")
        invalidate_cache("cached")
        m2 = load_manifest("cached")
        assert m1 is not m2
