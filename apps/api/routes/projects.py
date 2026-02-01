"""
Projects Blueprint
Handles /api/projects endpoints for multi-project support.
"""
import json
import logging

from flask import Blueprint, jsonify, send_from_directory, abort, request

from config import Config
from manifest import discover_projects, get_manifest, _manifest_cache
from middleware.auth import optional_auth

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/api/projects', methods=['GET'])
def list_projects():
    """Return list of available projects."""
    projects = discover_projects()
    return jsonify(projects)


@projects_bp.route('/api/projects/<slug>/manifest', methods=['GET'])
def get_project_manifest(slug):
    """Return full manifest for a specific project."""
    # Strict check: slug must exist as a subdirectory in PROJECTS_DIR
    project_dir = Config.PROJECTS_DIR / slug
    if not project_dir.is_dir() or not (project_dir / "project.json").exists():
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    try:
        manifest = get_manifest(slug)
        return jsonify(manifest.as_json())
    except RuntimeError as e:
        return jsonify({"status": "error", "error": str(e)}), 404


@projects_bp.route('/api/projects/<slug>/parts/<path:filename>', methods=['GET'])
def serve_static_part(slug, filename):
    """Serve a pre-existing STL file from a project's parts/ directory."""
    project_dir = Config.PROJECTS_DIR / slug
    parts_dir = project_dir / "parts"
    if not parts_dir.is_dir():
        abort(404)
    # Security: ensure filename doesn't escape parts_dir
    requested = (parts_dir / filename).resolve()
    if not str(requested).startswith(str(parts_dir.resolve())):
        abort(403)
    if not requested.is_file():
        abort(404)
    return send_from_directory(str(parts_dir), filename)


@projects_bp.route('/api/projects/<slug>/manifest/assembly-steps', methods=['PUT'])
@optional_auth
def update_assembly_steps(slug):
    """Update assembly_steps in a project's project.json."""
    project_dir = Config.PROJECTS_DIR / slug
    manifest_path = project_dir / "project.json"
    if not manifest_path.is_file():
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    data = request.get_json(silent=True)
    if not data or "assembly_steps" not in data:
        return jsonify({"status": "error", "error": "Missing assembly_steps"}), 400

    try:
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        manifest_data["assembly_steps"] = data["assembly_steps"]

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Invalidate manifest cache
        _manifest_cache.pop(slug, None)

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Failed to save assembly steps for {slug}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
