"""Tests for the Cotiza export blueprint (cotiza_export.py).

Covers:
- Helper functions: _map_process_type, _build_quote_request_payload,
  _extract_geometry_metrics, _send_to_cotiza
- Route-level integration: POST /api/projects/<slug>/cotiza-quote-request
  with 404, 409, 201, and 502 scenarios.

Auth and rate limiting are bypassed by the root conftest.py (AUTH_ENABLED=False,
limiter.enabled=False), matching the existing test patterns in this project.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.integrations.cotiza_export import (
    _build_quote_request_payload,
    _map_process_type,
    _send_to_cotiza,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_MANIFEST = {
    "name": "Test Cube",
    "description": "A test cube for quoting",
    "slug": "test-cube",
}

SAMPLE_GEOMETRY = {
    "volume_cm3": 12.5,
    "surface_area_cm2": 37.5,
    "bounding_box_mm": {"x": 25.0, "y": 25.0, "z": 20.0},
}


@pytest.fixture
def project_on_disk(tmp_path, monkeypatch):
    """Create a minimal project directory with manifest and a fake mesh file.

    Returns a tuple of (slug, project_dir, mesh_path).
    """
    from config import Config

    slug = "test-cube"
    project_dir = tmp_path / slug
    project_dir.mkdir()

    manifest = {
        "name": "Test Cube",
        "description": "A test cube for quoting",
        "slug": slug,
        "modes": [
            {
                "id": "default",
                "scad_file": "main.scad",
                "label": {"en": "Default"},
                "parts": ["body"],
                "estimate": {"base_units": 1, "formula": "constant"},
            }
        ],
        "parts": [
            {
                "id": "body",
                "render_mode": 0,
                "label": {"en": "Body"},
                "default_color": "#3498db",
            }
        ],
        "parameters": [],
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(25);")

    # Create a fake mesh file in the static dir so _find_latest_render can
    # discover it.  The file just needs to exist on disk with matching name.
    static_dir = tmp_path / "static"
    static_dir.mkdir(exist_ok=True)
    mesh_name = f"{slug}_{Config.STL_PREFIX}abc123_body.glb"
    mesh_path = static_dir / mesh_name
    mesh_path.write_bytes(b"\x00" * 64)  # dummy content

    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

    return slug, project_dir, str(mesh_path)


@pytest.fixture
def app(project_on_disk):
    """Create a Flask test application with the cotiza_export blueprint."""
    from app import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ===========================================================================
# Unit tests: _map_process_type
# ===========================================================================


class TestMapProcessType:
    """Verify that Yantra4D process hints map to Cotiza ProcessType enums."""

    @pytest.mark.parametrize(
        "input_val, expected",
        [
            ("fff", "3d_fff"),
            ("fdm", "3d_fff"),
            ("sla", "3d_sla"),
            ("cnc", "cnc_3axis"),
            ("laser", "laser_2d"),
            # Already-qualified values should pass through unchanged.
            ("3d_fff", "3d_fff"),
            ("3d_sla", "3d_sla"),
            ("cnc_3axis", "cnc_3axis"),
            ("laser_2d", "laser_2d"),
        ],
    )
    def test_known_process_mappings(self, input_val, expected):
        assert _map_process_type(input_val) == expected

    def test_case_insensitive(self):
        assert _map_process_type("FFF") == "3d_fff"
        assert _map_process_type("SLA") == "3d_sla"
        assert _map_process_type("Cnc") == "cnc_3axis"

    def test_unknown_process_defaults_to_3d_fff(self):
        assert _map_process_type("injection_molding") == "3d_fff"
        assert _map_process_type("") == "3d_fff"
        assert _map_process_type("unknown") == "3d_fff"


# ===========================================================================
# Unit tests: _build_quote_request_payload
# ===========================================================================


class TestBuildQuoteRequestPayload:
    """Verify the assembled payload structure and default handling."""

    def test_minimal_body_uses_defaults(self):
        payload = _build_quote_request_payload(
            slug="test-cube",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body={},
        )

        assert payload["source"] == "yantra4d"
        assert payload["market_verified"] is False
        assert payload["provenance"]["source"] == "yantra4d"
        assert payload["fallback_reason"] == "Quote request export only; market pricing is determined by Cotiza."
        assert payload["project"]["slug"] == "test-cube"
        assert payload["project"]["name"] == "Test Cube"
        assert payload["project"]["description"] == "A test cube for quoting"

        assert payload["geometry"] == SAMPLE_GEOMETRY

        item = payload["item"]
        assert item["material"] == "PLA"
        assert item["quantity"] == 1
        assert item["finish"] == "standard"
        assert item["process"] == "3d_fff"

        assert payload["currency"] == "MXN"
        assert payload["notes"] == ""

    def test_body_values_override_defaults(self):
        body = {
            "material": "ABS",
            "quantity": 5,
            "finish": "smooth",
            "process": "sla",
            "currency": "USD",
            "notes": "Urgent order",
        }
        payload = _build_quote_request_payload(
            slug="test-cube",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body=body,
        )

        assert payload["item"]["material"] == "ABS"
        assert payload["item"]["quantity"] == 5
        assert payload["item"]["finish"] == "smooth"
        assert payload["item"]["process"] == "3d_sla"
        assert payload["currency"] == "USD"
        assert payload["notes"] == "Urgent order"

    def test_quantity_floor_is_one(self):
        """Quantity must be at least 1, even if 0 or negative is passed."""
        payload = _build_quote_request_payload(
            slug="x",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body={"quantity": 0},
        )
        assert payload["item"]["quantity"] == 1

        payload_neg = _build_quote_request_payload(
            slug="x",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body={"quantity": -3},
        )
        assert payload_neg["item"]["quantity"] == 1

    def test_extra_body_keys_in_options(self):
        """Keys not consumed by top-level fields should appear in item.options."""
        body = {"color": "red", "infill": 20}
        payload = _build_quote_request_payload(
            slug="test-cube",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body=body,
        )
        opts = payload["item"]["options"]
        assert opts["color"] == "red"
        assert opts["infill"] == 20

    def test_reserved_keys_excluded_from_options(self):
        """Reserved keys (material, quantity, finish, process, notes, currency,
        mode, parameters) must NOT be duplicated into options."""
        body = {
            "material": "PETG",
            "quantity": 2,
            "finish": "matte",
            "process": "fff",
            "notes": "test",
            "currency": "USD",
            "mode": "default",
            "parameters": {"size": 10},
        }
        payload = _build_quote_request_payload(
            slug="test-cube",
            manifest=SAMPLE_MANIFEST,
            geometry=SAMPLE_GEOMETRY,
            body=body,
        )
        opts = payload["item"]["options"]
        # material and finish ARE in options by design (see source lines 180-181)
        assert "quantity" not in opts
        assert "process" not in opts
        assert "notes" not in opts
        assert "currency" not in opts
        assert "mode" not in opts
        assert "parameters" not in opts

    def test_manifest_name_fallback_to_slug(self):
        """When manifest has no 'name', slug is used as project name."""
        payload = _build_quote_request_payload(
            slug="my-slug",
            manifest={"description": "desc only"},
            geometry=SAMPLE_GEOMETRY,
            body={},
        )
        assert payload["project"]["name"] == "my-slug"
        assert payload["item"]["name"] == "my-slug"


# ===========================================================================
# Unit tests: _send_to_cotiza
# ===========================================================================


class TestSendToCotiza:
    """Verify HTTP interaction with the Cotiza API."""

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_successful_post(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"quote_id": "q-123", "total": 250.0}
        mock_post.return_value = mock_resp

        result = _send_to_cotiza({"source": "yantra4d"}, auth_token="tok-abc")
        assert result == {"quote_id": "q-123", "total": 250.0}

        # Verify auth header was sent
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer tok-abc"

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_timeout_raises_runtime_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(RuntimeError, match="timed out"):
            _send_to_cotiza({"source": "yantra4d"})

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_connection_error_raises_runtime_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(RuntimeError, match="Could not connect"):
            _send_to_cotiza({"source": "yantra4d"})

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_generic_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("network")

        with pytest.raises(RuntimeError, match="request failed"):
            _send_to_cotiza({"source": "yantra4d"})

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_http_error_status_raises_runtime_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"message": "Invalid material"}
        mock_resp.text = "Invalid material"
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="422.*Invalid material"):
            _send_to_cotiza({"source": "yantra4d"})

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_http_error_with_unparseable_body(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="500.*Internal Server Error"):
            _send_to_cotiza({"source": "yantra4d"})

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_no_api_key_omits_header(self, mock_post):
        """When COTIZA_API_KEY is empty, X-API-Key header should not be present."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        with patch("routes.integrations.cotiza_export.COTIZA_API_KEY", ""):
            _send_to_cotiza({"source": "yantra4d"})

        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "X-API-Key" not in headers

    @patch("routes.integrations.cotiza_export.requests.post")
    def test_api_key_sent_when_configured(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        with patch("routes.integrations.cotiza_export.COTIZA_API_KEY", "secret-key"):
            _send_to_cotiza({"source": "yantra4d"})

        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["X-API-Key"] == "secret-key"


# ===========================================================================
# Unit tests: _extract_geometry_metrics
# ===========================================================================


class TestExtractGeometryMetrics:
    """Verify trimesh-based geometry extraction and fallback behavior."""

    @patch("routes.integrations.cotiza_export.trimesh", create=True)
    def test_successful_extraction(self, mock_trimesh_mod):
        """Extracts volume, surface area, and bounding box from a valid mesh."""
        # We need to patch the import inside the function.  Since _extract_geometry_metrics
        # does `import trimesh` at function scope, we mock it via sys.modules.
        import numpy as np
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        mock_mesh = MagicMock()
        mock_mesh.is_volume = True
        mock_mesh.volume = 5000.0  # mm^3
        mock_mesh.area = 2500.0  # mm^2
        mock_mesh.bounds = np.array([[0.0, 0.0, 0.0], [10.0, 20.0, 30.0]])

        mock_trimesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        with patch.dict("sys.modules", {"trimesh": mock_trimesh}):
            result = _extract_geometry_metrics("/fake/mesh.glb")

        assert result["volume_cm3"] == 5.0  # 5000 / 1000
        assert result["surface_area_cm2"] == 25.0  # 2500 / 100
        assert result["bounding_box_mm"] == {"x": 10.0, "y": 20.0, "z": 30.0}

    def test_fallback_on_missing_trimesh(self):
        """When trimesh is not installed, returns zero metrics gracefully."""
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        # Force trimesh import to fail inside the function
        real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def failing_import(name, *args, **kwargs):
            if name == "trimesh":
                raise ImportError("no trimesh")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            result = _extract_geometry_metrics("/fake/mesh.stl")

        assert result["volume_cm3"] == 0.0
        assert result["surface_area_cm2"] == 0.0
        assert result["bounding_box_mm"] == {"x": 0, "y": 0, "z": 0}

    def test_fallback_on_corrupt_mesh(self):
        """When trimesh raises an error loading the mesh, returns zeros."""
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        mock_trimesh = MagicMock()
        mock_trimesh.load.side_effect = Exception("corrupt file")

        with patch.dict("sys.modules", {"trimesh": mock_trimesh}):
            result = _extract_geometry_metrics("/fake/corrupt.stl")

        assert result["volume_cm3"] == 0.0
        assert result["surface_area_cm2"] == 0.0

    def test_non_watertight_mesh_uses_zero_volume(self):
        """When mesh.is_volume is False, volume should be 0."""
        import numpy as np
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        mock_mesh = MagicMock()
        mock_mesh.is_volume = False
        mock_mesh.volume = -123.0  # unreliable for non-watertight
        mock_mesh.area = 800.0
        mock_mesh.bounds = np.array([[0.0, 0.0, 0.0], [5.0, 5.0, 5.0]])

        mock_trimesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        with patch.dict("sys.modules", {"trimesh": mock_trimesh}):
            result = _extract_geometry_metrics("/fake/open.stl")

        assert result["volume_cm3"] == 0.0
        assert result["surface_area_cm2"] == 8.0  # 800 / 100


# ===========================================================================
# Route integration tests: POST /api/projects/<slug>/cotiza-quote-request
# ===========================================================================


class TestCotizaQuoteRequestRoute:
    """Integration tests for the full endpoint using the Flask test client.

    Auth is disabled (AUTH_ENABLED=False via conftest) so @require_tier("pro")
    passes all requests through.  Rate limiting is also disabled.
    """

    def test_missing_project_returns_404(self, client):
        """Project slug not found on disk yields 404."""
        resp = client.post(
            "/api/projects/nonexistent-project/cotiza-quote-request",
            json={},
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert "not found" in data["error"].lower()

    def test_invalid_slug_returns_400(self, client):
        """Malformed slug rejected by @require_valid_slug."""
        resp = client.post(
            "/api/projects/AB/cotiza-quote-request",
            json={},
        )
        assert resp.status_code == 400

    @patch("routes.integrations.cotiza_export._find_latest_render", return_value=None)
    def test_no_rendered_mesh_returns_409(self, mock_find, client, project_on_disk):
        """When no mesh file exists, endpoint should return 409."""
        slug = project_on_disk[0]
        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={},
        )
        assert resp.status_code == 409
        data = resp.get_json()
        assert "render" in data["error"].lower() or "mesh" in data["error"].lower()

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_successful_quote_returns_201(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """Happy path: manifest found, mesh found, geometry extracted,
        Cotiza API returns success.  Endpoint should return 201."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = SAMPLE_GEOMETRY.copy()
        mock_send.return_value = {"quote_id": "q-999", "total": 150.0}

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={"material": "PETG", "quantity": 3, "process": "sla"},
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["project"] == slug
        assert data["cotiza_quote"]["quote_id"] == "q-999"
        assert data["geometry"]["volume_cm3"] == SAMPLE_GEOMETRY["volume_cm3"]
        assert data["market_verified"] is False
        assert data["provenance"]["source"] == "cotiza"

        # Verify the payload sent to Cotiza had correct process mapping
        sent_payload = mock_send.call_args[0][0]
        assert sent_payload["item"]["process"] == "3d_sla"
        assert sent_payload["item"]["material"] == "PETG"
        assert sent_payload["item"]["quantity"] == 3

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_cotiza_timeout_returns_502(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """When Cotiza API times out, endpoint returns 502."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = SAMPLE_GEOMETRY.copy()
        mock_send.side_effect = RuntimeError("Cotiza API request timed out")

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={},
        )

        assert resp.status_code == 502
        data = resp.get_json()
        assert "timed out" in data["error"].lower()
        assert data.get("error_code") == "COTIZA_API_ERROR"

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_cotiza_connection_error_returns_502(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """When Cotiza API is unreachable, endpoint returns 502."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = SAMPLE_GEOMETRY.copy()
        mock_send.side_effect = RuntimeError("Could not connect to Cotiza API")

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={},
        )

        assert resp.status_code == 502
        data = resp.get_json()
        assert "connect" in data["error"].lower()

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_empty_json_body_uses_defaults(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """When request body is empty or missing, defaults should be applied."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = SAMPLE_GEOMETRY.copy()
        mock_send.return_value = {"quote_id": "q-default"}

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            content_type="application/json",
            data="{}",
        )

        assert resp.status_code == 201
        sent_payload = mock_send.call_args[0][0]
        assert sent_payload["item"]["material"] == "PLA"
        assert sent_payload["item"]["quantity"] == 1
        assert sent_payload["item"]["process"] == "3d_fff"
        assert sent_payload["currency"] == "MXN"

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_auth_token_forwarded_to_cotiza(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """Bearer token from the request should be forwarded to Cotiza."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = SAMPLE_GEOMETRY.copy()
        mock_send.return_value = {"quote_id": "q-auth"}

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={},
            headers={"Authorization": "Bearer my-jwt-token"},
        )

        assert resp.status_code == 201
        # Check that auth_token was passed through
        call_kwargs = mock_send.call_args
        assert call_kwargs.kwargs.get("auth_token") == "my-jwt-token" or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == "my-jwt-token"
        )

    @patch("routes.integrations.cotiza_export._send_to_cotiza")
    @patch("routes.integrations.cotiza_export._extract_geometry_metrics")
    @patch("routes.integrations.cotiza_export._find_latest_render")
    def test_zero_geometry_still_sends_request(
        self, mock_find, mock_geo, mock_send, client, project_on_disk
    ):
        """Even when geometry metrics are all zero (invalid mesh), the
        request should still be sent to Cotiza (with a warning logged)."""
        slug = project_on_disk[0]

        mock_find.return_value = "/fake/mesh.glb"
        mock_geo.return_value = {
            "volume_cm3": 0.0,
            "surface_area_cm2": 0.0,
            "bounding_box_mm": {"x": 0, "y": 0, "z": 0},
        }
        mock_send.return_value = {"quote_id": "q-zero"}

        resp = client.post(
            f"/api/projects/{slug}/cotiza-quote-request",
            json={},
        )

        assert resp.status_code == 201
        mock_send.assert_called_once()

    def test_get_method_not_allowed(self, client, project_on_disk):
        """GET on the POST-only endpoint should return 405."""
        slug = project_on_disk[0]
        resp = client.get(f"/api/projects/{slug}/cotiza-quote-request")
        assert resp.status_code == 405
