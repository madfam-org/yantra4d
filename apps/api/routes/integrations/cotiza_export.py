"""
Cotiza Export Blueprint -- export quote requests from Yantra4D to Cotiza.

Endpoints:
  POST /api/projects/<slug>/cotiza-quote-request
      Renders geometry data, extracts volume/surface area from the latest
      render mesh, and sends a structured quote request payload to the
      Cotiza (digifab-quoting) API.

Environment:
  COTIZA_API_URL    -- Base URL of the Cotiza API (default: http://localhost:4000)
  COTIZA_API_KEY    -- API key for authenticating with Cotiza
"""

import json
import logging
import os
from pathlib import Path

import requests
from flask import Blueprint, g, jsonify, request

import rate_limits
from config import Config
from extensions import limiter
from middleware.auth import require_tier
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

cotiza_export_bp = Blueprint("cotiza_export", __name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COTIZA_API_URL = os.getenv("COTIZA_API_URL", "http://localhost:4000")
COTIZA_API_KEY = os.getenv("COTIZA_API_KEY", "")
COTIZA_TIMEOUT_SECONDS = int(os.getenv("COTIZA_TIMEOUT_SECONDS", "30"))

# Supported mesh extensions in preference order (same as analysis.py)
_MESH_EXTENSIONS = (".glb", ".stl", ".3mf")
_RESERVED_OPTION_KEYS = {
    "material",
    "quantity",
    "finish",
    "process",
    "notes",
    "currency",
    "mode",
    "parameters",
    "require_market_verified",
}


class CotizaAPIError(RuntimeError):
    """Cotiza returned an HTTP error that should retain its meaning."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str = "COTIZA_API_ERROR",
        body: dict | None = None,
    ):
        super().__init__(f"Cotiza API returned {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.body = body or {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_manifest(slug: str) -> dict | None:
    """Load project.json for the given project slug."""
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _find_latest_render(slug: str) -> str | None:
    """Locate the most recently modified render output for a project.

    Render files follow the naming convention:
        {slug}_preview_{hash}_{part}.{ext}
    stored in Config.STATIC_DIR.
    """
    import glob as glob_mod

    prefix = f"{slug}_{Config.STL_PREFIX}"
    static_folder = str(Config.STATIC_DIR)
    candidates: list[str] = []

    for ext in _MESH_EXTENSIONS:
        pattern = os.path.join(static_folder, f"{prefix}*{ext}")
        candidates.extend(glob_mod.glob(pattern))

    if not candidates:
        return None

    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def _extract_geometry_metrics(mesh_path: str) -> dict:
    """Extract volume and surface area from a mesh file using trimesh.

    Returns a dict with keys: volume_cm3, surface_area_cm2, bounding_box_mm.
    Falls back to zeros if trimesh is unavailable or the mesh cannot be loaded.
    """
    try:
        import trimesh

        mesh = trimesh.load(mesh_path, force="mesh")

        # trimesh returns volume in the mesh's native units (mm^3 for STL)
        volume_mm3 = abs(mesh.volume) if mesh.is_volume else 0.0
        surface_area_mm2 = mesh.area

        # Convert to cm^3 and cm^2
        volume_cm3 = volume_mm3 / 1000.0
        surface_area_cm2 = surface_area_mm2 / 100.0

        # Bounding box in mm
        bounds = mesh.bounds  # shape (2, 3) -- min and max corners
        bbox_mm = {
            "x": float(bounds[1][0] - bounds[0][0]),
            "y": float(bounds[1][1] - bounds[0][1]),
            "z": float(bounds[1][2] - bounds[0][2]),
        }

        return {
            "volume_cm3": round(volume_cm3, 4),
            "surface_area_cm2": round(surface_area_cm2, 4),
            "bounding_box_mm": bbox_mm,
        }
    except Exception as exc:
        logger.warning("Failed to extract geometry metrics from %s: %s", mesh_path, exc)
        return {
            "volume_cm3": 0.0,
            "surface_area_cm2": 0.0,
            "bounding_box_mm": {"x": 0, "y": 0, "z": 0},
        }


def _map_process_type(process: str) -> str:
    """Map a Yantra4D process hint to a Cotiza ProcessType enum value."""
    mapping = {
        "fff": "3d_fff",
        "fdm": "3d_fff",
        "sla": "3d_sla",
        "cnc": "cnc_3axis",
        "laser": "laser_2d",
        "3d_fff": "3d_fff",
        "3d_sla": "3d_sla",
        "cnc_3axis": "cnc_3axis",
        "laser_2d": "laser_2d",
    }
    return mapping.get(process.lower(), "3d_fff")


def _bool_from_body(value) -> bool:
    """Interpret JSON/env-style booleans without treating arbitrary strings as true."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _cotiza_error_from_response(resp) -> CotizaAPIError:
    """Build a typed error while preserving Cotiza's truth/error contract."""
    body = {}
    try:
        parsed = resp.json()
        if isinstance(parsed, dict):
            body = parsed
    except Exception:
        body = {}

    detail = body.get("detail") if isinstance(body.get("detail"), dict) else {}
    message = (
        body.get("message")
        or detail.get("message")
        or body.get("error")
        or resp.text
        or "Cotiza API error"
    )
    error_code = (
        body.get("error_code")
        or detail.get("code")
        or body.get("error")
        or "COTIZA_API_ERROR"
    )
    return CotizaAPIError(
        status_code=resp.status_code,
        message=str(message),
        error_code=str(error_code),
        body=body,
    )


def _cotiza_market_truth(cotiza_response: dict) -> dict:
    """Extract the downstream market truth labels without inventing them."""
    market_context = cotiza_response.get("market_context") or {}
    if not isinstance(market_context, dict):
        market_context = {}

    provenance = cotiza_response.get("provenance") or market_context.get("provenance") or {}
    if not isinstance(provenance, dict):
        provenance = {}

    market_verified = bool(
        cotiza_response.get(
            "market_verified",
            market_context.get(
                "market_verified",
                provenance.get("market_verified", False),
            ),
        )
    )
    status = str(cotiza_response.get("status", "")).lower()
    warnings = cotiza_response.get("warnings") or []
    needs_review = bool(cotiza_response.get("needs_review")) or status == "needs_review"

    return {
        "market_verified": market_verified,
        "market_context": market_context,
        "pricing_source": (
            cotiza_response.get("pricing_source")
            or market_context.get("pricing_source")
            or market_context.get("source")
            or provenance.get("source")
        ),
        "fallback_reason": (
            cotiza_response.get("fallback_reason")
            or market_context.get("fallback_reason")
            or provenance.get("fallback_reason")
        ),
        "needs_review": needs_review,
        "warnings": warnings,
    }


def _build_quote_request_payload(
    slug: str,
    manifest: dict,
    geometry: dict,
    body: dict,
) -> dict:
    """Assemble the quote request payload for the Cotiza API.

    The payload is structured to match what ``POST /api/v1/quotes/from-yantra4d``
    expects on the Cotiza side.
    """
    # Extract material from request body, fall back to manifest defaults
    material = body.get("material", "PLA")
    quantity = max(1, int(body.get("quantity", 1)))
    finish = body.get("finish", "standard")
    process = _map_process_type(body.get("process", "fff"))
    notes = body.get("notes", "")
    currency = body.get("currency", "MXN")
    require_market_verified = _bool_from_body(body.get("require_market_verified", False))

    # Pull project display info from manifest
    project_name = manifest.get("name", slug)
    project_description = manifest.get("description", "")
    options = {
        "material": material,
        "finish": finish,
        **{k: v for k, v in body.items() if k not in _RESERVED_OPTION_KEYS},
    }
    if body.get("mode") is not None:
        options["yantra4d_mode"] = body.get("mode")
    if body.get("parameters") is not None:
        options["yantra4d_parameters"] = body.get("parameters")

    return {
        "source": "yantra4d",
        "require_market_verified": require_market_verified,
        "provenance": {
            "source": "yantra4d",
            "system": "yantra4d",
            "market_verified": False,
            "fallback_reason": "Quote request export only; market pricing is determined by Cotiza.",
            "geometry_source": "latest_render_mesh",
            "mode": body.get("mode"),
        },
        "project": {
            "slug": slug,
            "name": project_name,
            "description": project_description,
        },
        "geometry": {
            "volume_cm3": geometry["volume_cm3"],
            "surface_area_cm2": geometry["surface_area_cm2"],
            "bounding_box_mm": geometry["bounding_box_mm"],
        },
        "item": {
            "name": project_name,
            "process": process,
            "material": material,
            "quantity": quantity,
            "finish": finish,
            "options": options,
        },
        "currency": currency,
        "notes": notes,
    }


def _send_to_cotiza(payload: dict, auth_token: str | None = None) -> dict:
    """POST the quote request payload to the Cotiza API.

    Returns the JSON response body on success.
    Raises RuntimeError on network or HTTP errors.
    """
    url = f"{COTIZA_API_URL}/api/v1/quotes/from-yantra4d"
    headers = {"Content-Type": "application/json"}

    if COTIZA_API_KEY:
        headers["X-API-Key"] = COTIZA_API_KEY
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=COTIZA_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Cotiza API request timed out")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Cotiza API")
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Cotiza API request failed: {exc}")

    if resp.status_code >= 400:
        raise _cotiza_error_from_response(resp)

    return resp.json()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@cotiza_export_bp.route(
    "/api/projects/<slug>/cotiza-quote-request",
    methods=["POST"],
)
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.COTIZA_EXPORT)
@handle_exceptions
def create_cotiza_quote_request(slug: str):
    """Export a quote request from a Yantra4D project to Cotiza.

    Expects a JSON body with fabrication preferences:
        material   (str)  -- Material name, e.g. "PLA", "ABS" (default: "PLA")
        quantity   (int)  -- Number of units to quote (default: 1)
        finish     (str)  -- Surface finish, e.g. "standard", "smooth" (default: "standard")
        process    (str)  -- Manufacturing process: fff|sla|cnc|laser (default: "fff")
        currency   (str)  -- Quote currency: "MXN" or "USD" (default: "MXN")
        notes      (str)  -- Free-text notes for the fabricator (default: "")
        mode       (str)  -- Manifest mode slug to render (optional)
        parameters (dict)  -- Render parameters override (optional)

    The endpoint:
      1. Loads the project manifest.
      2. Finds the latest rendered mesh (or triggers a render if needed).
      3. Extracts volume, surface area, and bounding box from the mesh.
      4. Assembles a structured quote request payload.
      5. Sends the payload to Cotiza's ``POST /api/v1/quotes/from-yantra4d``.
      6. Returns the Cotiza response (created quote details).

    Returns 201 on successful quote creation with the Cotiza response.
    Returns 404 if the project is not found.
    Returns 409 if no rendered mesh exists (render first).
    Returns 502 if the Cotiza API is unreachable or returns an error.
    """
    # -- Load manifest --
    manifest = _load_manifest(slug)
    if not manifest:
        return error_response(f"Project '{slug}' not found", 404)

    # -- Parse request body --
    body = request.get_json(silent=True) or {}

    # -- Locate latest render mesh --
    mesh_path = _find_latest_render(slug)
    if mesh_path is None:
        return error_response(
            f"No rendered mesh found for project '{slug}'. "
            "Please render the model first via POST /api/render.",
            409,
        )

    # -- Extract geometry metrics --
    geometry = _extract_geometry_metrics(mesh_path)

    if geometry["volume_cm3"] <= 0 and geometry["surface_area_cm2"] <= 0:
        logger.warning(
            "Geometry metrics are zero for %s -- mesh may be invalid. "
            "Proceeding with the quote request anyway.",
            slug,
        )

    # -- Build payload --
    payload = _build_quote_request_payload(slug, manifest, geometry, body)
    require_market_verified = payload["require_market_verified"]

    logger.info(
        "Sending quote request to Cotiza for project '%s' "
        "[volume=%.2f cm3, material=%s, qty=%d, process=%s] "
        "[request_id=%s]",
        slug,
        geometry["volume_cm3"],
        payload["item"]["material"],
        payload["item"]["quantity"],
        payload["item"]["process"],
        getattr(g, "request_id", None),
    )

    # -- Forward auth token if present --
    auth_header = request.headers.get("Authorization", "")
    auth_token = None
    if auth_header.lower().startswith("bearer "):
        auth_token = auth_header[7:]

    # -- Send to Cotiza --
    try:
        cotiza_response = _send_to_cotiza(payload, auth_token=auth_token)
    except CotizaAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        error_code = exc.error_code
        if exc.status_code == 424 or error_code == "market_data_unavailable":
            status_code = 424
            error_code = "MARKET_DATA_UNAVAILABLE"
        logger.error(
            "Cotiza export failed for '%s' [request_id=%s status=%d code=%s]: %s",
            slug,
            getattr(g, "request_id", None),
            exc.status_code,
            exc.error_code,
            exc.message,
        )
        return error_response(exc.message, status_code, error_code=error_code)
    except RuntimeError as exc:
        logger.error(
            "Cotiza export failed for '%s' [request_id=%s]: %s",
            slug,
            getattr(g, "request_id", None),
            exc,
        )
        return error_response(str(exc), 502, error_code="COTIZA_API_ERROR")

    market_truth = _cotiza_market_truth(cotiza_response)
    if require_market_verified and not market_truth["market_verified"]:
        logger.error(
            "Cotiza returned unverified quote despite strict market verification "
            "for '%s' [request_id=%s fallback_reason=%s]",
            slug,
            getattr(g, "request_id", None),
            market_truth["fallback_reason"],
        )
        return error_response(
            "Market-verified ForgeSight pricing was required, but Cotiza did not return a verified market context.",
            424,
            error_code="MARKET_DATA_UNAVAILABLE",
        )

    client_ready = market_truth["market_verified"] and not market_truth["needs_review"]

    return jsonify({
        "status": "success",
        "project": slug,
        "cotiza_quote": cotiza_response,
        "geometry": geometry,
        "source": "cotiza",
        "market_verified": market_truth["market_verified"],
        "market_context": market_truth["market_context"],
        "pricing_source": market_truth["pricing_source"],
        "fallback_reason": market_truth["fallback_reason"],
        "needs_review": market_truth["needs_review"],
        "client_ready": client_ready,
        "provenance": {
            "source": "cotiza",
            "upstream_request_source": "yantra4d",
            "market_verified": market_truth["market_verified"],
            "pricing_source": market_truth["pricing_source"],
            "fallback_reason": market_truth["fallback_reason"],
            "needs_review": market_truth["needs_review"],
        },
    }), 201
