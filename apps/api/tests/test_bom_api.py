"""Tests for BOM API endpoint."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _create_project(tmp_path, slug="bom-test", bom=None, parameters=None):
    """Create a test project with optional BOM."""
    project_dir = tmp_path / slug
    project_dir.mkdir(exist_ok=True)
    manifest = {
        "project": {"name": "BOM Test", "slug": slug, "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": "Default",
                    "parts": ["main"], "estimate": {"base_units": 1}}],
        "parts": [{"id": "main", "render_mode": 0, "label": "Main", "default_color": "#fff"}],
        "parameters": parameters or [
            {"id": "enable_magnets", "type": "checkbox", "default": 0},
            {"id": "width_units", "type": "slider", "default": 2, "min": 1, "max": 6},
            {"id": "depth_units", "type": "slider", "default": 1, "min": 1, "max": 6},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 1, "per_part": 1},
    }
    if bom is not None:
        manifest["bom"] = bom
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    return project_dir


@pytest.fixture
def app(tmp_path):
    hardware = [
        {
            "id": "magnets",
            "label": {"en": "Magnets", "es": "Imanes"},
            "quantity_formula": "(enable_magnets * 4) + (width_units * depth_units)",
            "unit": "pcs",
        },
        {
            "id": "screws",
            "label": {"en": "Screws"},
            "quantity_formula": 8,
            "unit": "pcs",
            "supplier_url": "https://example.com",
        },
    ]
    _create_project(tmp_path, bom={"hardware": hardware})
    _create_project(tmp_path, slug="no-bom")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestBomAPI:
    def test_get_bom_json(self, client):
        res = client.get("/api/projects/bom-test/bom")
        assert res.status_code == 200
        data = res.get_json()
        assert "bom" in data
        assert len(data["bom"]) == 2
        assert data["bom"][0]["id"] == "magnets"
        assert data["bom"][1]["id"] == "screws"

    def test_bom_evaluates_formulas_with_defaults(self, client):
        res = client.get("/api/projects/bom-test/bom")
        data = res.get_json()
        # enable_magnets=False(0), width_units=2, depth_units=1
        # (0 * 4) + (2 * 1) = 2
        assert data["bom"][0]["quantity"] == 2
        # Static formula = 8
        assert data["bom"][1]["quantity"] == 8

    def test_bom_evaluates_with_query_params(self, client):
        res = client.get("/api/projects/bom-test/bom?enable_magnets=1&width_units=3&depth_units=2")
        data = res.get_json()
        # (1 * 4) + (3 * 2) = 10
        assert data["bom"][0]["quantity"] == 10

    def test_bom_csv_format(self, client):
        res = client.get("/api/projects/bom-test/bom?format=csv")
        assert res.status_code == 200
        assert res.content_type.startswith("text/csv")
        text = res.data.decode()
        assert "magnets" in text
        assert "screws" in text

    def test_bom_csv_via_accept_header(self, client):
        res = client.get("/api/projects/bom-test/bom", headers={"Accept": "text/csv"})
        assert res.status_code == 200
        assert res.content_type.startswith("text/csv")

    def test_bom_includes_unit_and_label(self, client):
        res = client.get("/api/projects/bom-test/bom")
        data = res.get_json()
        assert data["bom"][0]["unit"] == "pcs"
        assert data["bom"][0]["label"] == "Magnets"
        assert data["bom"][1]["supplier_url"] == "https://example.com"

    def test_bom_404_unknown_project(self, client):
        res = client.get("/api/projects/nonexistent/bom")
        assert res.status_code == 404

    def test_bom_404_no_bom_in_project(self, client):
        res = client.get("/api/projects/no-bom/bom")
        assert res.status_code == 404
        data = res.get_json()
        assert "No BOM" in data["error"]


class TestSafeEvalFormula:
    """Tests for AST-based formula evaluator security."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from routes.bom import _safe_eval_formula
        self.eval_formula = _safe_eval_formula

    def test_rejects_import(self):
        with pytest.raises(ValueError, match="Unsafe"):
            self.eval_formula("__import__('os').system('rm -rf /')", {})

    def test_rejects_builtins(self):
        with pytest.raises(ValueError, match="Unsafe"):
            self.eval_formula("eval('1+1')", {})

    def test_rejects_attribute_access(self):
        with pytest.raises(ValueError, match="Unsafe"):
            self.eval_formula("(1).__class__", {})

    def test_rejects_string_literals(self):
        with pytest.raises(ValueError, match="Unsafe"):
            self.eval_formula("'malicious'", {})

    def test_nested_parens(self):
        result = self.eval_formula("((2 + 3) * (4 - 1))", {})
        assert result == 15

    def test_division(self):
        result = self.eval_formula("10 / 2", {})
        assert result == 5.0

    def test_unary_negative(self):
        result = self.eval_formula("-5 + 10", {})
        assert result == 5

    def test_param_substitution(self):
        result = self.eval_formula("x * y + 1", {"x": 3, "y": 4})
        assert result == 13

    def test_numeric_passthrough(self):
        assert self.eval_formula(42, {}) == 42
        assert self.eval_formula(3.14, {}) == 3.14
