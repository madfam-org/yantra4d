"""/api/openapi.json and /api/llms.txt (A1 E-4: both answered 404 live)."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_SPEC = Path(__file__).resolve().parents[4] / "docs" / "reference" / "openapi.yaml"


@pytest.fixture
def client():
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_openapi_json_is_the_validated_document(client):
    res = client.get("/api/openapi.json")
    assert res.status_code == 200
    assert res.mimetype == "application/json"
    assert "max-age" in res.headers["Cache-Control"]
    served = res.get_json()
    assert served == yaml.safe_load(REPO_SPEC.read_text(encoding="utf-8"))
    assert served["openapi"].startswith("3.")
    # The document describes itself and the routes this change touched.
    assert "/api/openapi.json" in served["paths"]
    assert "/api/llms.txt" in served["paths"]
    assert "404" in served["paths"]["/api/render"]["post"]["responses"]


def test_openapi_json_missing_document_is_503_not_empty(client, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAPI_SPEC_PATH", str(tmp_path / "absent.yaml"))
    res = client.get("/api/openapi.json")
    assert res.status_code == 503
    assert res.get_json()["error_code"] == "openapi_unavailable"


def test_openapi_json_unparseable_document_is_503(client, monkeypatch, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("just: a mapping\n")
    monkeypatch.setenv("OPENAPI_SPEC_PATH", str(bad))
    res = client.get("/api/openapi.json")
    assert res.status_code == 503


def test_llms_txt_points_at_the_contract(client):
    res = client.get("/api/llms.txt")
    assert res.status_code == 200
    assert res.mimetype == "text/plain"
    text = res.get_data(as_text=True)
    assert text.startswith("# Yantra4D API")
    assert "/api/openapi.json" in text
    for route in ("/api/projects", "/api/render", "/api/estimate"):
        assert route in text
    assert "project_not_found" in text and "invalid_parameter" in text


def test_every_route_llms_txt_names_is_in_the_spec(client):
    import re
    text = client.get("/api/llms.txt").get_data(as_text=True)
    paths = client.get("/api/openapi.json").get_json()["paths"]
    named = set(re.findall(r"(?:GET|POST)\s+(/api/[^\s,]+)", text))
    assert named
    for route in named:
        assert route in paths, f"llms.txt names {route}, which the OpenAPI document does not describe"
