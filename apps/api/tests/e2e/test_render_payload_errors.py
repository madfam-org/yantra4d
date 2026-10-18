"""Render/estimate requests that name a missing project or send a bad parameter.

Before: an unknown ``project`` raised ``RuntimeError`` out of
``resolve_render_context`` and ``@handle_exceptions`` answered 500
INTERNAL_ERROR; a non-numeric value for a slider was dropped by
``validate_params`` and the default rendered with 200. Both are caller errors
and now answer with the standard error body (``status``/``error``/
``error_code``/``request_id``).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

SLUG = "payload-errors-project"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    project_dir = tmp_path / SLUG
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
                    "name": "Payload Errors", "slug": SLUG, "version": "1.0.0"},
        "modes": [
            {"id": "single", "scad_file": "main.scad", "label": {"en": "Single"}, "parts": ["main"],
             "estimate": {"base_units": 1, "formula": "constant"}},
        ],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [
            {"id": "width", "type": "slider", "default": 10, "min": 1, "max": 100, "label": {"en": "Width"}},
            {"id": "label_text", "type": "text", "default": "hi", "label": {"en": "Label"}},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(width);")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _assert_error_shape(res, status, code):
    assert res.status_code == status, res.get_data(as_text=True)
    body = res.get_json()
    assert body["status"] == "error"
    assert body["error_code"] == code
    assert isinstance(body["error"], str) and body["error"]
    assert body.get("request_id"), "standard error body carries the request id"
    return body


class TestUnknownProject:
    @pytest.mark.parametrize("route", ["/api/render", "/api/render-stream"])
    def test_render_routes_answer_404(self, client, route):
        res = client.post(route, json={"project": "no-such-project", "mode": "single", "parameters": {}})
        body = _assert_error_shape(res, 404, "project_not_found")
        assert "no-such-project" in body["error"]
        # The slug, never a filesystem path (manifest.py keeps paths out of bodies).
        assert "/" not in body["error"]

    def test_estimate_answers_404(self, client):
        res = client.post("/api/estimate", json={"project": "no-such-project", "mode": "single"})
        _assert_error_shape(res, 404, "project_not_found")


class TestInvalidNumericParameter:
    @pytest.mark.parametrize("value", ["abc;system(\"id\")", "", "nan", "inf", [1], {"x": 1}])
    @pytest.mark.parametrize("route", ["/api/render", "/api/render-stream"])
    def test_non_numeric_slider_is_400_naming_the_parameter(self, client, route, value):
        res = client.post(route, json={"project": SLUG, "mode": "single", "parameters": {"width": value}})
        body = _assert_error_shape(res, 400, "invalid_parameter")
        assert body["parameter"] == "width"
        assert "width" in body["error"]

    def test_flattened_payload_is_checked_too(self, client):
        res = client.post("/api/render", json={"project": SLUG, "mode": "single", "width": "abc"})
        body = _assert_error_shape(res, 400, "invalid_parameter")
        assert body["parameter"] == "width"


class TestValidPayloadsStillResolve:
    """The new checks refuse only what they name; everything else resolves as before."""

    @pytest.mark.parametrize("value", [42, 42.5, "42", None, True])
    def test_numeric_values_resolve(self, client, value):
        from services.engine.render_orchestrator import RenderPayloadError, extract_render_payload
        with client.application.test_request_context():
            payload = extract_render_payload({"project": SLUG, "mode": "single", "parameters": {"width": value}})
        assert not isinstance(payload, RenderPayloadError), getattr(payload, "message", payload)

    def test_non_slider_and_unknown_keys_are_not_checked(self, client):
        from services.engine.render_orchestrator import RenderPayloadError, extract_render_payload
        with client.application.test_request_context():
            payload = extract_render_payload({
                "project": SLUG, "mode": "single",
                "parameters": {"label_text": "abc", "not_declared": "abc"},
            })
        assert not isinstance(payload, RenderPayloadError), getattr(payload, "message", payload)
