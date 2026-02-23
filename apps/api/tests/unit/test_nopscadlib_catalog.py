"""Unit tests for services.core.nopscadlib_catalog."""
import pytest

import services.core.nopscadlib_catalog as cat_mod
from services.core.nopscadlib_catalog import get_catalog, list_categories


@pytest.fixture(autouse=True)
def _clear_lru_cache():
    """Clear the lru_cache on get_catalog before every test."""
    get_catalog.cache_clear()
    yield
    get_catalog.cache_clear()


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------
class TestListCategories:
    def test_returns_known_categories(self):
        cats = list_categories()
        assert "ball_bearings" in cats
        assert "stepper_motors" in cats

    def test_returns_list_type(self):
        cats = list_categories()
        assert isinstance(cats, list)
        assert all(isinstance(c, str) for c in cats)


# ---------------------------------------------------------------------------
# get_catalog
# ---------------------------------------------------------------------------
class TestGetCatalog:
    def test_unknown_category_returns_empty(self):
        """Unknown category key returns an empty list."""
        assert get_catalog("nonexistent") == []

    def test_ball_bearings_parsing(self, tmp_path, monkeypatch):
        """Parses ball_bearings.scad format and extracts correct fields."""
        scad = tmp_path / "ball_bearings.scad"
        scad.write_text(
            'BB608 = ["608", 8, 22, 7, "Chrome"];\n'
            'BB624 = ["624", 4, 13, 5, "Silver"];\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)

        result = get_catalog("ball_bearings")
        assert len(result) == 2

        bb608 = result[0]
        assert bb608["id"] == "608"
        assert bb608["category"] == "ball_bearings"
        assert bb608["specs"]["bore_diameter"] == 8.0
        assert bb608["specs"]["outer_diameter"] == 22.0
        assert bb608["specs"]["width"] == 7.0
        assert bb608["specs"]["color"] == "Chrome"
        assert bb608["parameters"]["bore_diameter"] == 8.0
        assert "608" in bb608["label"]
        assert "608" in bb608["supplier_search"]

    def test_stepper_motors_parsing(self, tmp_path, monkeypatch):
        """Parses stepper_motors.scad format and extracts correct fields."""
        scad = tmp_path / "stepper_motors.scad"
        scad.write_text(
            'NEMA17_40 = ["NEMA17x40", 42.3, 40, 2.5, 24];\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)

        result = get_catalog("stepper_motors")
        assert len(result) == 1

        motor = result[0]
        assert motor["id"] == "NEMA17x40"
        assert motor["category"] == "stepper_motors"
        assert motor["specs"]["nema_size"] == 17
        assert motor["specs"]["frame_width"] == 42.3
        assert motor["specs"]["body_length"] == 40.0
        assert motor["parameters"]["nema_size"] == 17
        assert "NEMA 17" in motor["label"]

    def test_stepper_motors_deduplicates(self, tmp_path, monkeypatch):
        """Duplicate motor IDs are deduplicated (only first occurrence kept)."""
        scad = tmp_path / "stepper_motors.scad"
        scad.write_text(
            'NEMA17_40  = ["NEMA17x40", 42.3, 40, 2.5, 24];\n'
            'NEMA17_40L = ["NEMA17x40", 42.3, 40, 2.5, 24];\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)

        result = get_catalog("stepper_motors")
        assert len(result) == 1

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        """Returns empty list when the .scad file does not exist."""
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)
        assert get_catalog("ball_bearings") == []

    def test_multiple_entries_ball_bearings(self, tmp_path, monkeypatch):
        """Parses multiple entries from a single ball_bearings file."""
        lines = [
            'BB608 = ["608", 8, 22, 7, "Chrome"];',
            'BB624 = ["624", 4, 13, 5, "Silver"];',
            'BB6200 = ["6200", 10, 30, 9, "Chrome"];',
        ]
        scad = tmp_path / "ball_bearings.scad"
        scad.write_text("\n".join(lines), encoding="utf-8")
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)

        result = get_catalog("ball_bearings")
        assert len(result) == 3
        ids = [r["id"] for r in result]
        assert ids == ["608", "624", "6200"]

    def test_caching_via_lru(self, tmp_path, monkeypatch):
        """Second call with same category returns cached result (lru_cache)."""
        scad = tmp_path / "ball_bearings.scad"
        scad.write_text('BB608 = ["608", 8, 22, 7, "Chrome"];\n', encoding="utf-8")
        monkeypatch.setattr(cat_mod, "_VITAMINS_DIR", tmp_path)

        first = get_catalog("ball_bearings")
        # Overwrite file — cached result should still be returned
        scad.write_text("// empty", encoding="utf-8")
        second = get_catalog("ball_bearings")
        assert first is second
        assert len(second) == 1
