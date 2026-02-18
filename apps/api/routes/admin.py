"""
Admin Blueprint
Provides /api/admin/* endpoints for project management and monitoring.
"""
import json
import logging
import os
from pathlib import Path

from flask import Blueprint, jsonify, request, Response

from config import Config
from manifest import discover_projects, get_manifest
from middleware.auth import require_role
from services.route_helpers import error_response

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Flags that the admin UI is allowed to toggle
_ALLOWED_FLAGS = {"is_demo", "is_hyperobject"}


def _load_raw_manifest(slug: str) -> dict | None:
    """Load raw project.json dict (not the parsed ManifestService object)."""
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _save_raw_manifest(slug: str, data: dict) -> None:
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _enrich_project(proj):
    """Add computed metadata to a project dict."""
    project_dir = Config.PROJECTS_DIR / proj["slug"]
    manifest_path = project_dir / "project.json"

    proj["has_manifest"] = manifest_path.exists()
    proj["modified_at"] = (
        os.path.getmtime(manifest_path) if manifest_path.exists() else None
    )

    scad_files = list(project_dir.glob("*.scad"))
    proj["scad_file_count"] = len(scad_files)

    exports_dir = project_dir / "exports"
    proj["has_exports"] = (
        exports_dir.is_dir() and any(exports_dir.glob("*.stl"))
    )

    if proj["has_manifest"]:
        try:
            m = get_manifest(proj["slug"])
            proj["mode_count"] = len(m.modes)
            proj["parameter_count"] = len(m.parameters)
            proj["estimate_constants"] = m.estimate_constants
        except Exception:
            proj["mode_count"] = 0
            proj["parameter_count"] = 0
            proj["estimate_constants"] = None

        # Expose admin-managed flags from raw manifest
        raw = _load_raw_manifest(proj["slug"]) or {}
        project_obj = raw.get("project", {})
        proj["is_demo"] = project_obj.get("is_demo", False)
        ho = project_obj.get("hyperobject", {})
        proj["is_hyperobject"] = ho.get("is_hyperobject", False)
    else:
        proj["mode_count"] = 0
        proj["parameter_count"] = 0
        proj["estimate_constants"] = None
        proj["is_demo"] = False
        proj["is_hyperobject"] = False

    return proj


@admin_bp.route('/api/admin/projects', methods=['GET'])
@require_role("admin")
def admin_list_projects() -> Response:
    """Return enriched list of all projects."""
    projects = discover_projects()
    enriched = [_enrich_project(p) for p in projects]
    return jsonify(enriched)


@admin_bp.route('/api/admin/projects/<slug>', methods=['GET'])
@require_role("admin")
def admin_project_detail(slug: str) -> Response | tuple[Response, int]:
    """Return detailed info for a single project."""
    project_dir = Config.PROJECTS_DIR / slug
    manifest_path = project_dir / "project.json"

    if not project_dir.is_dir() or not manifest_path.exists():
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    projects = discover_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj:
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    proj = _enrich_project(proj)

    # SCAD files with sizes
    scad_files = []
    for f in sorted(project_dir.glob("*.scad")):
        scad_files.append({"name": f.name, "size": f.stat().st_size})
    proj["scad_files"] = scad_files

    # Modes detail
    try:
        m = get_manifest(slug)
        proj["modes"] = [
            {"id": mode["id"], "label": mode.get("label", mode["id"]), "scad_file": mode["scad_file"]}
            for mode in m.modes
        ]
    except Exception:
        proj["modes"] = []

    # Exports with sizes
    exports = []
    exports_dir = project_dir / "exports"
    if exports_dir.is_dir():
        for f in sorted(exports_dir.glob("*.stl")):
            exports.append({"name": f.name, "size": f.stat().st_size})
    proj["exports"] = exports

    return jsonify(proj)


@admin_bp.route('/api/admin/projects/<slug>/flags', methods=['PATCH'])
@require_role("admin")
def patch_project_flags(slug: str) -> Response | tuple[Response, int]:
    """
    Toggle is_demo and/or is_hyperobject flags for a project.

    Body (JSON):
      { "is_demo": true, "is_hyperobject": false }

    Only keys present in the body are updated; others are left unchanged.
    Writes directly to projects/<slug>/project.json.
    """
    raw = _load_raw_manifest(slug)
    if raw is None:
        return error_response(f"Project '{slug}' not found", 404)

    body = request.get_json(silent=True) or {}
    unknown = set(body.keys()) - _ALLOWED_FLAGS
    if unknown:
        return error_response(f"Unknown flags: {sorted(unknown)}", 400)

    project_obj = raw.setdefault("project", {})
    changed = {}

    if "is_demo" in body:
        val = bool(body["is_demo"])
        project_obj["is_demo"] = val
        changed["is_demo"] = val

    if "is_hyperobject" in body:
        val = bool(body["is_hyperobject"])
        ho = project_obj.setdefault("hyperobject", {})
        ho["is_hyperobject"] = val
        changed["is_hyperobject"] = val

    if not changed:
        return error_response("No valid flags provided", 400)

    try:
        _save_raw_manifest(slug, raw)
    except OSError as exc:
        logger.exception("Failed to write project.json for %s", slug)
        return error_response(f"Failed to save: {exc}", 500)

    logger.info("Admin updated flags for %s: %s", slug, changed)
    return jsonify({"slug": slug, "updated": changed})


@admin_bp.route('/api/admin/projects/tablaco/public-link', methods=['GET'])
@require_role("admin")
def tablaco_public_link() -> Response:
    """
    Return the public storefront URL for the tablaco project.

    This is the ONLY endpoint that exposes the tablaco public link.
    Protected by admin role — not available in any public API.
    """
    public_base = os.getenv("PUBLIC_STUDIO_URL", "").rstrip("/")
    if not public_base:
        # Fallback: derive from request host (works for local dev)
        public_base = request.host_url.rstrip("/")

    url = f"{public_base}/studio#tablaco?mode=storefront"

    return jsonify({
        "slug": "tablaco",
        "public_url": url,
        "note": "Share this URL to give customers access to the Tablaco storefront.",
    })
