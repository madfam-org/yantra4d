"""
Projects Blueprint
Handles /api/projects endpoints for multi-project support.
"""
from flask import Blueprint, jsonify

from config import Config
from manifest import discover_projects, get_manifest

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
