"""Unit tests for services.core.material_service."""
import json

import pytest

import services.core.material_service as mat_mod


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    """Ensure module-level cache is cleared before every test."""
    monkeypatch.setattr(mat_mod, "_materials_cache", None)


@pytest.fixture
def materials_dir(tmp_path, monkeypatch):
    """Point get_materials_dir() at a temporary directory."""
    monkeypatch.setattr(mat_mod, "get_materials_dir", lambda: tmp_path)
    return tmp_path


def _write_material(base_dir, slug, extra=None):
    """Helper: create <base_dir>/<slug>/material.json with valid content."""
    sub = base_dir / slug
    sub.mkdir(parents=True, exist_ok=True)
    payload = {"material": {"slug": slug, "name": slug.upper(), "category": "thermoplastic"}}
    if extra:
        payload["material"].update(extra)
    (sub / "material.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


# ---------------------------------------------------------------------------
# discover_materials
# ---------------------------------------------------------------------------
class TestDiscoverMaterials:
    def test_empty_directory(self, materials_dir):
        """No subdirectories returns empty list."""
        result = mat_mod.discover_materials()
        assert result == []

    def test_nonexistent_directory(self, tmp_path, monkeypatch):
        """Non-existent materials dir returns empty list without raising."""
        monkeypatch.setattr(mat_mod, "get_materials_dir", lambda: tmp_path / "nope")
        result = mat_mod.discover_materials()
        assert result == []

    def test_discovers_valid_material(self, materials_dir):
        """Discovers and parses a valid material.json in a subdirectory."""
        expected = _write_material(materials_dir, "pla")
        result = mat_mod.discover_materials()
        assert len(result) == 1
        assert result[0]["material"]["slug"] == "pla"
        assert result[0] == expected

    def test_discovers_multiple_materials(self, materials_dir):
        """Discovers all valid materials across multiple subdirectories."""
        _write_material(materials_dir, "pla")
        _write_material(materials_dir, "petg")
        _write_material(materials_dir, "abs")
        result = mat_mod.discover_materials()
        slugs = {m["material"]["slug"] for m in result}
        assert slugs == {"pla", "petg", "abs"}

    def test_skips_invalid_json(self, materials_dir):
        """Skips subdirectories with malformed material.json."""
        bad_dir = materials_dir / "corrupt"
        bad_dir.mkdir()
        (bad_dir / "material.json").write_text("{not valid json", encoding="utf-8")
        result = mat_mod.discover_materials()
        assert result == []

    def test_skips_dirs_without_manifest(self, materials_dir):
        """Skips subdirectories that lack a material.json file."""
        empty_dir = materials_dir / "no-manifest"
        empty_dir.mkdir()
        (empty_dir / "readme.md").write_text("hello")
        result = mat_mod.discover_materials()
        assert result == []

    def test_caching(self, materials_dir):
        """Second call returns cached result without re-scanning the filesystem."""
        _write_material(materials_dir, "pla")
        first = mat_mod.discover_materials()
        assert len(first) == 1

        # Add another material on disk — should NOT appear due to cache
        _write_material(materials_dir, "petg")
        second = mat_mod.discover_materials()
        assert len(second) == 1
        assert second is first  # same object reference (cached)

    def test_force_refresh(self, materials_dir):
        """force_refresh=True re-scans even when cached."""
        _write_material(materials_dir, "pla")
        first = mat_mod.discover_materials()
        assert len(first) == 1

        _write_material(materials_dir, "petg")
        refreshed = mat_mod.discover_materials(force_refresh=True)
        assert len(refreshed) == 2


# ---------------------------------------------------------------------------
# get_material
# ---------------------------------------------------------------------------
class TestGetMaterial:
    def test_found(self, materials_dir):
        """Returns the material dict when the slug matches."""
        _write_material(materials_dir, "pla")
        result = mat_mod.get_material("pla")
        assert result["material"]["slug"] == "pla"
        assert result["material"]["name"] == "PLA"

    def test_not_found_raises(self, materials_dir):
        """Raises RuntimeError for an unknown slug."""
        _write_material(materials_dir, "pla")
        with pytest.raises(RuntimeError, match="not found"):
            mat_mod.get_material("unknown-slug")
