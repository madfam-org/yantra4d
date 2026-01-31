"""
Admin Blueprint
Provides /api/admin/* endpoints for project management and monitoring.
"""
import os

from flask import Blueprint, jsonify

from config import Config
from manifest import discover_projects, get_manifest

admin_bp = Blueprint('admin', __name__)


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
        except Exception:
            proj["mode_count"] = 0
            proj["parameter_count"] = 0
    else:
        proj["mode_count"] = 0
        proj["parameter_count"] = 0

    return proj


@admin_bp.route('/api/admin/projects', methods=['GET'])
def admin_list_projects():
    """Return enriched list of all projects."""
    projects = discover_projects()
    enriched = [_enrich_project(p) for p in projects]
    return jsonify(enriched)


@admin_bp.route('/api/admin/projects/<slug>', methods=['GET'])
def admin_project_detail(slug):
    """Return detailed info for a single project."""
    project_dir = Config.PROJECTS_DIR / slug
    manifest_path = project_dir / "project.json"

    if not project_dir.is_dir() or not manifest_path.exists():
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    # Start from discover_projects entry
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
