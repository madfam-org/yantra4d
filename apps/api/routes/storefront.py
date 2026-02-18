"""
Storefront Blueprint — customer-facing view of a project.

Endpoints:
  GET /api/projects/<slug>/storefront
      Returns a storefront-safe manifest: developer fields stripped,
      only customer-relevant data exposed.

  GET /api/projects/<slug>/share/<preset_id>
      Returns a shareable configuration URL for a specific preset.
"""

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import Config
from services.route_helpers import error_response

storefront_bp = Blueprint("storefront", __name__)
logger = logging.getLogger(__name__)

# Fields stripped from the storefront manifest (developer-only)
_STRIP_PARAM_FIELDS = {"group", "visibility_level", "hidden", "visible_in_modes"}
_STRIP_MODE_FIELDS = {"scad_file", "estimate"}
_STRIP_ROOT_FIELDS = {
    "estimate_constants", "verification", "parameter_groups",
    "export_formats",
}


def _load_manifest(slug: str) -> dict | None:
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _sanitize_for_storefront(manifest: dict, mode_id: str | None = None) -> dict:
    """
    Return a copy of the manifest with developer-only fields removed.
    Optionally filter parameters to a specific mode.
    """
    import copy
    m = copy.deepcopy(manifest)

    # Strip root-level developer fields
    for field in _STRIP_ROOT_FIELDS:
        m.pop(field, None)

    # Strip developer fields from parameters
    params = m.get("parameters", [])
    filtered_params = []
    for p in params:
        # Skip hidden parameters
        if p.get("hidden"):
            continue
        # Filter by mode if requested
        if mode_id and "visible_in_modes" in p:
            if mode_id not in p["visible_in_modes"]:
                continue
        # Strip developer-only fields
        clean = {k: v for k, v in p.items() if k not in _STRIP_PARAM_FIELDS}
        filtered_params.append(clean)
    m["parameters"] = filtered_params

    # Strip developer fields from modes
    for mode in m.get("modes", []):
        for field in _STRIP_MODE_FIELDS:
            mode.pop(field, None)

    return m


@storefront_bp.route("/api/projects/<slug>/storefront", methods=["GET"])
def get_storefront_manifest(slug: str):
    """
    Return a storefront-safe manifest for the given project.
    Query params:
      ?mode=<mode_id>  — filter parameters to this mode only
    """
    manifest = _load_manifest(slug)
    if not manifest:
        return error_response(f"Project '{slug}' not found", 404)

    mode_id = request.args.get("mode")
    safe = _sanitize_for_storefront(manifest, mode_id)

    return jsonify({
        "slug": slug,
        "storefront": True,
        "manifest": safe,
    })


@storefront_bp.route("/api/projects/<slug>/share/<preset_id>", methods=["GET"])
def get_share_url(slug: str, preset_id: str):
    """
    Return a shareable URL for a specific preset configuration.
    The URL encodes the preset's parameter values as query params.
    """
    manifest = _load_manifest(slug)
    if not manifest:
        return error_response(f"Project '{slug}' not found", 404)

    presets = manifest.get("presets", [])
    preset = next((p for p in presets if p.get("id") == preset_id), None)
    if not preset:
        return error_response(f"Preset '{preset_id}' not found in project '{slug}'", 404)

    # Build query string from preset values
    values = preset.get("values", {})
    qs = "&".join(f"{k}={v}" for k, v in values.items())

    # Determine base URL from request host
    base = request.host_url.rstrip("/")
    share_url = f"{base}/studio#{slug}?mode=storefront&preset={preset_id}&{qs}"

    return jsonify({
        "slug": slug,
        "preset_id": preset_id,
        "preset_label": preset.get("label", preset_id),
        "values": values,
        "share_url": share_url,
    })
