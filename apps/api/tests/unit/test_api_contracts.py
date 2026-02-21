import json
from pathlib import Path
import yaml
import pytest
from openapi_schema_validator import validate

# ---------------------------------------------------------------------------
# OpenAPI Setup
# ---------------------------------------------------------------------------

OPENAPI_PATH = Path(__file__).parent.parent.parent.parent.parent / "docs" / "reference" / "openapi.yaml"
with open(OPENAPI_PATH, "r") as f:
    OPENAPI_SPEC = yaml.safe_load(f)

def assert_matches_schema(data, schema_name):
    """Validate a Python dict against a schema component in the OpenAPI spec."""
    schema = OPENAPI_SPEC["components"]["schemas"][schema_name]
    try:
        validate(data, schema)
    except Exception as e:
        pytest.fail(f"OpenAPI validation failed: {e}")
    
    
    # However we can just resolve refs manually or use the built-in RefResolver mapping the whole spec
    # A cleaner approach using the core jsonschema validation against the sub-schema:
    from jsonschema import RefResolver
    resolver = RefResolver.from_schema(OPENAPI_SPEC)
    
    try:
        validate(instance=data, schema=schema, resolver=resolver)
    except Exception as e:
        pytest.fail(f"JSON schema validation failed for {schema_name}: {e}")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project on disk and return its slug."""
    slug = "contract-test"
    project_dir = tmp_path / slug
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", 
            "name": "Contract Test Project",
            "slug": slug,
            "version": "1.0.0",
            "description": {"en": "Test project for contract validation", "es": "Proyecto de prueba"}
        },
        "modes": [
            {
                "id": "default",
                "scad_file": "main.scad",
                "label": {"en": "Default", "es": "Predeterminado"},
                "parts": ["body"],
                "estimate": {"base_units": 1, "formula": "constant"},
            }
        ],
        "parts": [
            {
                "id": "body",
                "render_mode": 0,
                "label": {"en": "Body", "es": "Cuerpo"},
                "default_color": "#3498db",
            }
        ],
        "parameters": [
            {
                "id": "size",
                "type": "slider",
                "default": 10,
                "min": 5,
                "max": 50,
                "step": 1,
                "label": {"en": "Size", "es": "Tamaño"},
                "visible_in_modes": ["default"],
            }
        ],
        "presets": [
            {
                "id": "small",
                "label": {"en": "Small", "es": "Pequeño"},
                "values": {"size": 10},
            }
        ],
        "estimate_constants": {
            "base_time": 5,
            "per_unit": 2,
            "per_part": 8,
            "fn_factor": 48,
            "wasm_multiplier": 3,
            "warning_threshold_seconds": 60,
        },
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube($size);")
    return slug


@pytest.fixture
def app(sample_project):
    from app import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class TestHealthContract:
    def test_returns_200(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert_matches_schema(res.get_json(), "HealthResponse")

    def test_has_required_fields(self, client):
        data = client.get("/api/health").get_json()
        assert "status" in data
        assert "openscad_available" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["openscad_available"], bool)


# ---------------------------------------------------------------------------
# /api/projects
# ---------------------------------------------------------------------------

class TestProjectsListContract:
    def test_returns_200(self, client):
        res = client.get("/api/projects")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        for d in data:
            assert_matches_schema(d, "ProjectSummary")

    def test_returns_array(self, client):
        data = client.get("/api/projects").get_json()
        assert isinstance(data, list)

    def test_project_entry_shape(self, client, sample_project):
        data = client.get("/api/projects").get_json()
        assert len(data) >= 1
        entry = next((p for p in data if p["slug"] == sample_project), None)
        assert entry is not None
        # Required fields
        assert "slug" in entry
        assert "name" in entry


# ---------------------------------------------------------------------------
# /api/projects/<slug>/manifest
# ---------------------------------------------------------------------------

class TestManifestContract:
    def test_returns_200(self, client, sample_project):
        res = client.get(f"/api/projects/{sample_project}/manifest")
        assert res.status_code == 200
        assert_matches_schema(res.get_json(), "Manifest")

    def test_has_top_level_keys(self, client, sample_project):
        data = client.get(f"/api/projects/{sample_project}/manifest").get_json()
        for key in ("project", "modes", "parts", "parameters", "estimate_constants"):
            assert key in data, f"Missing top-level key: {key}"

    def test_project_section_shape(self, client, sample_project):
        data = client.get(f"/api/projects/{sample_project}/manifest").get_json()
        proj = data["project"]
        assert proj["slug"] == sample_project
        assert isinstance(proj["name"], str)
        assert isinstance(proj["version"], str)

    def test_modes_are_array(self, client, sample_project):
        data = client.get(f"/api/projects/{sample_project}/manifest").get_json()
        modes = data["modes"]
        assert isinstance(modes, list)
        assert len(modes) >= 1
        mode = modes[0]
        for key in ("id", "scad_file", "label", "parts", "estimate"):
            assert key in mode, f"Mode missing key: {key}"

    def test_parts_are_array(self, client, sample_project):
        data = client.get(f"/api/projects/{sample_project}/manifest").get_json()
        parts = data["parts"]
        assert isinstance(parts, list)
        assert len(parts) >= 1
        part = parts[0]
        for key in ("id", "render_mode", "label", "default_color"):
            assert key in part, f"Part missing key: {key}"

    def test_parameters_are_array(self, client, sample_project):
        data = client.get(f"/api/projects/{sample_project}/manifest").get_json()
        params = data["parameters"]
        assert isinstance(params, list)
        if len(params) > 0:
            p = params[0]
            for key in ("id", "type", "default"):
                assert key in p, f"Parameter missing key: {key}"

    def test_nonexistent_project_returns_404(self, client):
        res = client.get("/api/projects/nonexistent-slug/manifest")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# /api/estimate
# ---------------------------------------------------------------------------

class TestEstimateContract:
    def test_returns_200(self, client, sample_project):
        res = client.post(
            "/api/estimate",
            json={"project": sample_project, "mode": "default", "scad_file": "main.scad", "parameters": {}},
        )
        assert res.status_code == 200
        assert_matches_schema(res.get_json(), "EstimateResponse")

    def test_has_estimated_seconds(self, client, sample_project):
        data = client.post(
            "/api/estimate",
            json={"project": sample_project, "mode": "default", "scad_file": "main.scad", "parameters": {}},
        ).get_json()
        assert "estimated_seconds" in data
        assert isinstance(data["estimated_seconds"], (int, float))
        assert data["estimated_seconds"] > 0


# ---------------------------------------------------------------------------
# /api/render (shape validation only — no real OpenSCAD)
# ---------------------------------------------------------------------------

class TestRenderContract:
    def test_missing_mode_returns_400(self, client):
        res = client.post("/api/render", json={})
        assert res.status_code == 400

    def test_bad_mode_returns_error(self, client, sample_project):
        res = client.post(
            "/api/render",
            json={"project": sample_project, "mode": "nonexistent", "scad_file": "main.scad", "parameters": {}},
        )
        # Should get 400 or 404 for invalid mode
        assert res.status_code in (400, 404, 500)
